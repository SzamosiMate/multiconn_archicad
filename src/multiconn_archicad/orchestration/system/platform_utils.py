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


def escape_spaces_in_path(path):
    if is_using_windows():
        return f'"{path}"'
    else:
        return path.replace(" ", "\\ ")


def is_using_mac():
    return platform.system() == "Darwin"


def is_using_windows():
    return platform.system() == "Windows"
