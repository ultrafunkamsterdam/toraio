import asyncio
import toraio._pool


class Proxy:

    pool = toraio.Pool().start()

    def __init__(
        self, host="127.0.0.1", port=8888, proxy_host="httpbin.org", proxy_port=80
    ):
        self.host = host
        self.port = port
        self.proxy_port = proxy_port
        self.proxy_host = proxy_host

    async def pipe(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            while not reader.at_eof():
                writer.write(await reader.read(2048))
        finally:
            writer.close()

    async def handle_client(
        self, local_reader: asyncio.StreamReader, local_writer: asyncio.StreamWriter
    ):
        try:
            remote_reader, remote_writer = await self.pool.open_connection(
                self.proxy_host, self.proxy_port
            )
            pipe1 = self.pipe(local_reader, remote_writer)
            pipe2 = self.pipe(remote_reader, local_writer)
            await asyncio.gather(pipe1, pipe2)
        finally:
            local_writer.close()

    async def start(self):
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        await self.server.start_serving()
        print("Serving on {}".format(self.server.sockets[0].getsockname()))
        asyncio.ensure_future(self.server.serve_forever())
        return self


# keep reference to proxypool
pool = Proxy.pool


if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    proxy = Proxy()
    try:
        loop.run_until_complete(proxy.start())
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    proxy.server.close()
    loop.run_until_complete(proxy.server.wait_closed())
    loop.close()
