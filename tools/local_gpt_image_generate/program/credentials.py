from __future__ import annotations

import ctypes
from ctypes import wintypes
import os


CREDENTIAL_TARGET = "Tiance/local-gpt-image-8317"
ENVIRONMENT_VARIABLE = "TIANCE_LOCAL_IMAGE_API_KEY"
_CRED_TYPE_GENERIC = 1


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.c_void_p),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def load_api_key() -> str:
    environment_value = str(os.environ.get(ENVIRONMENT_VARIABLE) or "").strip()
    if environment_value:
        return environment_value
    if os.name != "nt":
        return ""
    return _read_windows_credential(CREDENTIAL_TARGET).strip()


def _read_windows_credential(target: str) -> str:
    credential_pointer = ctypes.POINTER(_Credential)()
    advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    advapi32.CredReadW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(_Credential)),
    ]
    advapi32.CredReadW.restype = wintypes.BOOL
    advapi32.CredFree.argtypes = [ctypes.c_void_p]
    advapi32.CredFree.restype = None
    if not advapi32.CredReadW(target, _CRED_TYPE_GENERIC, 0, ctypes.byref(credential_pointer)):
        return ""
    try:
        credential = credential_pointer.contents
        if not credential.CredentialBlob or credential.CredentialBlobSize <= 0:
            return ""
        raw = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
        return raw.decode("utf-16-le").rstrip("\x00")
    finally:
        advapi32.CredFree(credential_pointer)
