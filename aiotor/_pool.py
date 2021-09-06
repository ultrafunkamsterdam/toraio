import asyncio
import atexit
import re
import logging
import os
import socket
import subprocess
import sys
from collections import deque
import weakref

import aiohttp.client
import aiosocks.connector
import socks
import tempfile
import shutil


from . import _ua as UA
from ._util import free_port

# sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

DEFAULT_NUM_PROXIES = 10
MIN_PORT = 22222
MODULE_PATH = os.path.abspath(os.path.dirname(__file__))
IS_WIN = sys.platform.startswith("win32")
SEMA = asyncio.Semaphore(25)

__all__ = ["Pool",]


class Pool(object):
    _instance = None

    @classmethod
    def get_instance(cls):
        return cls._instance

    def __new__(cls, *args, **kwargs):
        if cls._instance:
            return cls._instance
        return object.__new__(cls)

    def __init__(
        self,
        num_ports=10,
        control_port=0,
        dns_port=0,
        new_circuit_period=15,
        cookie_auth=0,
        enforce_distinct_subnets=0,
        data_dir=None,
    ):
        """

        :param num_ports:
        :param control_port:
        :param dns_port:
        :param new_circuit_period:
        :param cookie_auth:
        :param enforce_distinct_subnets:
        """

        self._ports = None
        self.config = None
        self.proxies_iter = None
        self.num_ports = num_ports
        self.control_port = control_port
        self.cookie_auth = cookie_auth
        self.dns_port = dns_port
        self.new_circuit_period = new_circuit_period
        self.enforce_distinct_subnets = enforce_distinct_subnets
        self.data_dir = data_dir or tempfile.mkdtemp(prefix="tor_")
        self._clean_datadir = not bool(data_dir)
        self.process = None
        self.current = None

        self.proxies = deque()
        self.max_retry = 5

        self._controller = None
        self._hold = None
        self.__orig_sock = None
        try:
            logging.getLogger("pool").info("Starting Pool %s" % (hex(id(self))))
            self.start()
        except Exception as e:
            logging.getLogger("pool").exception(
                "Exception in init %s" % e, exc_info=True
            )

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
        :return:
        """
        logging.getLogger("pool").info("starting proxy pool")
        instance = self.get_instance()
        if instance:
            self.config = instance.config
        if self.running:
            return self
        else:
            self._ports = []
            for _ in range(self.num_ports):
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

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs,
        )

        self.proxies.clear()
        self.proxies.extend([Socks5Proxy("127.0.0.1", port) for port in self._ports])

        self.__class__._instance = self
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

        logging.info("stopping proxy pool")
        logging.info(
            "instance: %s,  datadir: %s , message: :%s "
            % (cls._instance, datadir, message)
        )

        if cls._instance.process:
            try:
                cls._instance.process.terminate()
                cls._instance.process.kill()
                logging.getLogger("pool").warning(
                    "cls instance killed %s" % cls._instance.process
                )
            except (ProcessLookupError, AttributeError, OSError, PermissionError):
                pass
        if cls._instance._clean_datadir:
            cls._rmtree(cls._instance.data_dir)

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
            logging.getLogger("Pool").warning(e)
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


class Socks5Proxy(aiosocks.Socks5Addr):
    @property
    def url(self):
        return f"socks5://{self.host}:{self.port}"

    def __str__(self):
        return "%s:%d" % (self.host, self.port)


class ClientSession(aiohttp.ClientSession):
    _instance = None

    def __init__(self, pool: Pool, **kw):
        if not kw.get("headers"):
            kw["headers"] = {}
        if not kw["headers"].get("user-agent"):
            kw["headers"]["user-agent"] = UA.GENERIC_WEBKIT
        # if not kw.get('timeout'):
        #     kw['timeout'] = aiohttp.ClientTimeout(5.0)
        super().__init__(
            connector=aiosocks.connector.ProxyConnector(
                ssl=False,
                remote_resolve=True,
            ),
            request_class=aiosocks.connector.ProxyClientRequest,
            **kw,
        )
        self.pool = pool
        self.__class__._instance = self

    def _request(self, *args, **kwargs):

        proxy = next(self.pool).url
        logging.getLogger("aiotor.ClientSession").info("proxy: %s" % proxy)
        kwargs["proxy"] = proxy
        return super(ClientSession, self)._request(*args, **kwargs)


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

    logging.basicConfig(level=10)

    pool = Pool()
    asyncio.run(start_test())
