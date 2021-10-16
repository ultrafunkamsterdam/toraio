import asyncio
import logging
from ._pool import Pool


class PoolForwardProxy:
    def __init__(
        self,
        pool: Pool,
        fw_host: str,
        fw_port: int,
        listen_host="0.0.0.0",
        listen_port=80080,
    ):

        self._server: asyncio.base_events.Server = None
        self.fw_host = fw_host
        self.fw_port = fw_port
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.pool = None

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """

        :param reader:
        :param writer:
        :return:
        """
        peer = writer.get_extra_info("peername")
        logging.getLogger(__name__).debug("connection from %s:%d" % peer)

        async def Pipe(r: asyncio.StreamReader, w: asyncio.StreamWriter):
            data = b""
            try:
                while True:
                    chunk = await r.read(1024)
                    if not chunk:
                        break
                    data += chunk
                    w.write(chunk)
                    await w.drain()
            except Exception as e:
                logging.getLogger(__name__).exception(e, exc_info=True)
            w.close()
            return data

        pool = Pool.get_instance()
        if not pool:
            logging.warning("no pool found. starting pool now.")
            pool = Pool().start()

        if not pool.running:
            raise Exception("pool not running")

        r, w = await pool.open_connection(
            self.fw_host, self.fw_port, remote_resolve=True
        )

        coro1, coro2 = Pipe(reader, w), Pipe(r, writer)
        data1, data2 = await asyncio.gather(coro1, coro2)
        print(data1)
        print(data2)

    async def __aenter__(self):
        self._server = await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        return True

    async def stop(self):
        try:
            self._server.close()
            await self._server.wait_closed()
        except Exception as e:
            print("ssmall", e)

    async def start(self):

        serv = await asyncio.start_server(
            self.handle_client, host=self.listen_host, port=self.listen_port
        )
        await serv.start_serving()
        return serv
