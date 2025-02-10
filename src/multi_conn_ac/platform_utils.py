import platform

def escape_colons_and_slashes(url: str) -> str:
    return url.replace(":", "%253A").replace("/", "%252F")

def escape_spaces_in_path(path):
    if is_using_windows():
        return f'"{path}"'
    else:
        return path.replace(" ", "\\ ")

def is_using_mac():
    return platform.system() == "Darwin"


def is_using_windows():
    return platform.system() == "Windows"