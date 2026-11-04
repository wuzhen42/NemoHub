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

_check_fingerprint = getattr(_lib, 'nemo_check_fingerprint', None) if _available else None
if _check_fingerprint is not None:
    _check_fingerprint.argtypes = [ctypes.c_char_p]
    _check_fingerprint.restype = ctypes.c_bool


def getFingerprint() -> str:
    if not _available:
        return ''
    result = _lib.nemo_get_fingerprint()
    return result.decode() if result else ''


def validateFingerprint(stored: str) -> bool:
    if not stored or '\0' in stored:
        return False
    if _check_fingerprint is None:
        return stored == getFingerprint()
    return bool(_check_fingerprint(stored.encode()))
