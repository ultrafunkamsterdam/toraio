import aiosocks2.connector
import aiohttp
import logging

from ._pool import Pool
from . import _ua as UA


class ClientSession(aiohttp.ClientSession):
    _instance = None

    def __init__(self, pool: Pool = None, **kw):
        if not pool:
            existing = Pool.get_instance()
            if not existing or not existing.running:
                # there is only 1 instance of Pool
                pool = Pool().start()
            else:
                pool = existing

        if not kw.get("headers"):
            kw["headers"] = {}
        if not kw["headers"].get("user-agent"):
            kw["headers"]["user-agent"] = UA.GENERIC_WEBKIT
        super().__init__(
            connector=aiosocks2.connector.ProxyConnector(
                ssl=False,
                remote_resolve=True,
            ),
            request_class=aiosocks2.connector.ProxyClientRequest,
            **kw,
        )
        self.pool = pool
        self.__class__._instance = self

    async def _request(self, *args, **kwargs):

        proxy = next(self.pool).url
        logging.getLogger(__name__).debug("proxy switched")
        kwargs["proxy"] = proxy
        return await super(ClientSession, self)._request(*args, **kwargs)
