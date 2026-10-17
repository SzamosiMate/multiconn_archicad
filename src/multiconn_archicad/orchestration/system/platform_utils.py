import platform
from urllib.parse import quote


def double_quote(url: str) -> str:
    url = quote(url, safe="")
    url = quote(url, safe="")
    url = url.replace(".", "%2E")
    return url


def single_quote(url: str) -> str:
    url = quote(url, safe="")
    url = url.replace(".", "%2E")
    return url


def is_using_mac():
    return platform.system() == "Darwin"


def is_using_windows():
    return platform.system() == "Windows"
