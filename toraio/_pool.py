import asyncio
import re
import logging
import os
import socket
import subprocess
import sys
from collections import deque
import weakref


import aiosocks2.connector
import socks
import tempfile
import shutil

from ._util import free_port


DEFAULT_NUM_PROXIES = 10
MIN_PORT = 22222
MODULE_PATH = os.path.abspath(os.path.dirname(__file__))
IS_WIN = sys.platform.startswith("win32")
SEMA = asyncio.Semaphore(25)

__all__ = ["Pool"]


class Pool(object):

    __state__ = {}
    __instance__ = None

    @classmethod
    def get_instance(cls):
        return cls.__instance__

    def __init__(
        self,
        amount=10,
        new_circuit_period=15,
        cookie_auth=0,
        enforce_distinct_subnets=0,
        data_dir=None,
    ):
        """

        :param amount:
        :param new_circuit_period:
        :param cookie_auth:
        :param enforce_distinct_subnets:
        :param data_dir:
        """
        self.__dict__ = self.__state__
        if not self.__state__:
            # no existing pool exists
            self.cookie_auth = cookie_auth
            self.amount = amount

            self.config = None
            self.control_port = None
            self.dns_port = None
            self.new_circuit_period = new_circuit_period
            self.enforce_distinct_subnets = enforce_distinct_subnets
            self.data_dir = data_dir or tempfile.mkdtemp(prefix="tor_")
            self.should_clean_data_dir = not bool(data_dir)
            self.process = None
            self.current = None

            self.proxies = deque()
            self.max_retry = 5

            self._controller = None
            self._hold = None
            self._ports = None
            self.__orig_sock = None
            self._finalizer = None

    @classmethod
    def _rmtree(cls, name):
        logging.getLogger("pool").info("performing rmtree on %s" % name)
        shutil.rmtree(name, ignore_errors=False)

    def cleanup(self):
        if self._finalizer.detach():
            logging.getLogger("pool").info("cleaning up after finalizer detached")
            self.stop(self.data_dir, "stopping trough cleanup")
            self._rmtree(self.data_dir)

    def start(self):
        """

        :return self:
        """
        instance = self.__instance__
        if instance is not None:
            # return instance
            if instance.process:
                if instance.process.poll() is None:
                    logging.getLogger(__name__).debug(
                        "already initialized. returning running instance"
                    )
                    return instance
            self.config = instance.config

        if not self.config:
            self._ports = []
            for _ in range(self.amount):
                self._ports.append(free_port())

            self.control_port = free_port()
            self.dns_port = free_port()

            self.config = [
                *("--SocksPort %d" % p for p in self._ports),
                "--ControlPort %d" % self.control_port,
                "--DnsPort %d" % self.dns_port,
                "--NewCircuitPeriod %d" % self.new_circuit_period,
                "--CookieAuthentication %s" % self.cookie_auth,
                "--EnforceDistinctSubnets %d" % self.enforce_distinct_subnets,
                "--DataDirectory %s" % self.data_dir,
            ]

        self.process = None
        exe_path = os.path.join(
            MODULE_PATH, "bin", sys.platform, "Tor", "tor.exe" if IS_WIN else "tor"
        )
        cmd = [exe_path] + " ".join(self.config).split()

        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["preexec_fn"] = os.setsid

        logging.getLogger("pool").info("starting proxy pool %s" % hex(id(self)))
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs,
        )

        self.proxies.clear()
        self.proxies.extend([Socks5Proxy("127.0.0.1", port) for port in self._ports])

        self.__class__.__instance__ = self
        logging.getLogger("stem").setLevel(20)
        self._finalizer = weakref.finalize(
            self, self.stop, self.data_dir, "implicitly cleaning up resources"
        )

        bootstrapping = True
        while bootstrapping:
            line = self.process.stdout.readline()
            percent = re.search(b"(?smi)bootstrapped ([\d]+)", line)
            if not percent:
                continue
            else:
                percent = float(percent[1])  # first group match
            logging.getLogger("pool").info("tor bootstrap %s completed" % percent)
            if percent > 95:
                bootstrapping = False

        return self

    @classmethod
    def stop(cls, datadir=None, message=None):
        if cls.__instance__.process:
            logging.getLogger(__name__).debug(
                "stopping proxy pool \ninstance: %s,  datadir: %s , message: :%s"
                % (cls.__instance__, datadir, message)
            )
            try:
                cls.__instance__.process.terminate()
                cls.__instance__.process.kill()
                logging.getLogger(__name__).debug(
                    "cls instance killed %s" % cls.__instance__.process
                )
            except (ProcessLookupError, AttributeError, OSError, PermissionError):
                pass
        if cls.__instance__.should_clean_data_dir:
            cls._rmtree(cls.__instance__.data_dir)

    @property
    def running(self):
        try:
            return self.process.poll() is None
        except:  # noqa
            return False

    def __repr__(self):
        return "{0.__class__.__name__!s}(running={0.running!s})\n\t{1}".format(
            self, "\n\t".join(str(x) for x in self.proxies)
        )

    def __iter__(self):
        return self

    def __enter__(self):
        next(self)
        self.__orig_sock = socket.socket
        socks.set_default_proxy(
            socks.PROXY_TYPE_SOCKS5,
            addr=self.current.host,
            port=self.current.port,
            rdns=True,
        )
        socket.socket = socks.socksocket
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if any([exc_type, exc_val, exc_tb]):
            print(exc_type, exc_val, exc_tb)
        socket.socket = self.__orig_sock

    def __next__(self):
        now = self.proxies.popleft()
        self.proxies.append(now)
        self.current = now
        return self.current

    def create_new_circuits(self):
        self._hold = True
        try:
            from stem import Signal

            self.controller.signal(Signal.NEWNYM)
        except Exception as e:
            logging.getLogger(__name__).warning(e)
        finally:
            self._hold = False

    @property
    def controller(self):
        if not self._controller:
            from stem.control import Controller

            self._controller = Controller.from_port(port=self.control_port)
        self._controller.authenticate()
        return self._controller

    def _stream_listener(self, event):
        try:
            circ = self.controller.get_circuit(event.circ_id)
            exit_fingerprint = circ.path[-1][0]
            exit_relay = self.controller.get_network_status(exit_fingerprint)
            self.current.exit_ip = exit_relay.address
        except Exception as e:
            logging.getLogger("stem.streamevents").debug(e)

    async def open_connection(self, host, port, remote_resolve=True, **kw):
        proxy = next(self)
        logging.getLogger(str(proxy)).debug("open_connection %s : %d " % (host, port))
        return await aiosocks2.open_connection(
            proxy, None, dst=(host, port), remote_resolve=remote_resolve, **kw
        )


class Socks5Proxy(aiosocks2.Socks5Addr):
    @property
    def url(self):
        return f"socks5://{self.host}:{self.port}"

    def __str__(self):
        return "%s:%d" % (self.host, self.port)


def test():
    async def fetch_test():
        for _ in range(10):
            print(await (await ClientSession(pool).get("http://httpbin.org/ip")).read())

    async def new_circuits_test():
        print("creating new circuits")
        pool.create_new_circuits()

    async def start_test():
        await fetch_test()
        await new_circuits_test()
        await fetch_test()
        await fetch_test()
        await new_circuits_test()
        await fetch_test()

    import logging
    from toraio import ClientSession

    logging.basicConfig(level=10)

    pool = Pool()
    asyncio.run(start_test())
