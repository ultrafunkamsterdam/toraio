import re
import socket

from contextlib import closing

_RE_CAMEL_TO_SNAKE = re.compile("((?!^)(?<!_)[A-Z][a-z]+|(?<=[a-z0-9])[A-Z])")
_RE_SNAKE_TO_CAMEL = re.compile("(.*?)_([a-zA-Z])")


def camel_to_snake(s):
    """
    Converts CamelCase/camelCase to snake_case
    :param str s: string to be converted
    :return: (str) snake_case version of s
    """
    return _RE_CAMEL_TO_SNAKE.sub(r"_\1", s).lower()


def snake_to_camel(s):
    """
    Converts snake_case_string to camelCaseString
    :param str s: string to be converted
    :return: (str) camelCase version of s
    """
    return _RE_SNAKE_TO_CAMEL.sub(lambda m: m.group(1) + m.group(2).upper(), s, 0)


def free_port():
    """
    Determines a free port using sockets.
    """
    free_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    free_socket.setsockopt(
        socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
    )  # reuse to prevent windows socket in use
    free_socket.bind(("0.0.0.0", 0))
    free_socket.listen(5)
    port = free_socket.getsockname()[1]
    free_socket.close()
    return port
