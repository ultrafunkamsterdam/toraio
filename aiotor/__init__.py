from ._pool import Pool, ClientSession
from . import _ua as ua
from . import _util as util


def start():
    return Pool().start()
