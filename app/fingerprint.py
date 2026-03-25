import ctypes
import pathlib
import sys

_lib_name = 'NemoFingerprint.dll' if sys.platform == 'win32' else 'libNemoFingerprint.so'
_lib_path = pathlib.Path(__file__).parent / _lib_name

try:
    _lib = ctypes.CDLL(str(_lib_path))
    _lib.nemo_get_fingerprint.restype = ctypes.c_char_p
    _available = True
except OSError:
    _available = False


def getFingerprint() -> str:
    if not _available:
        return ''
    result = _lib.nemo_get_fingerprint()
    return result.decode() if result else ''
