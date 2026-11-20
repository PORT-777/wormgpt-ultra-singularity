# core/memory_manager.py
# Language: Python 3 | Runtime: CPython | Target: Windows 11
# Low-level memory management via Windows API. Anti-crash by design.

from __future__ import annotations

import ctypes
import struct
from ctypes import wintypes
from typing import Optional

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_ALL_ACCESS = 0x1F0FFF

PAGE_NOACCESS = 0x01
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000


class MemoryManager:
    """Windows process memory reader/writer via OpenProcess/ReadProcessMemory/
    WriteProcessMemory/VirtualProtectEx/VirtualAllocEx. Every call validates
    the handle and surfaces Win32 errors as values (OSError), never crashes."""

    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.handle: Optional[int] = None

    def open(self, desired_access: int = PROCESS_ALL_ACCESS) -> bool:
        self.handle = kernel32.OpenProcess(desired_access, False, self.pid)
        if not self.handle:
            err = ctypes.get_last_error()
            raise OSError(f"OpenProcess failed for PID {self.pid}: error {err}")
        return True

    def close(self) -> None:
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None

    def read(self, address: int, size: int) -> bytes:
        if not self.handle:
            raise RuntimeError("Process handle not opened")
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t(0)
        ok = kernel32.ReadProcessMemory(
            self.handle,
            ctypes.c_void_p(address),
            buf,
            size,
            ctypes.byref(read),
        )
        if not ok:
            err = ctypes.get_last_error()
            raise OSError(f"ReadProcessMemory failed at {hex(address)}: error {err}")
        return buf.raw[: read.value]

    def write(self, address: int, data: bytes) -> int:
        if not self.handle:
            raise RuntimeError("Process handle not opened")
        buf = ctypes.create_string_buffer(data, len(data))
        written = ctypes.c_size_t(0)
        ok = kernel32.WriteProcessMemory(
            self.handle,
            ctypes.c_void_p(address),
            buf,
            len(data),
            ctypes.byref(written),
        )
        if not ok:
            err = ctypes.get_last_error()
            raise OSError(f"WriteProcessMemory failed at {hex(address)}: error {err}")
        return written.value

    def read_ptr(self, address: int, bits: int = 64) -> int:
        size = 8 if bits == 64 else 4
        raw = self.read(address, size)
        fmt = "<Q" if bits == 64 else "<I"
        return struct.unpack(fmt, raw)[0]

    def write_ptr(self, address: int, value: int, bits: int = 64) -> int:
        size = 8 if bits == 64 else 4
        fmt = "<Q" if bits == 64 else "<I"
        return self.write(address, struct.pack(fmt, value))

    def protect(self, address: int, size: int, new_protect: int) -> int:
        if not self.handle:
            raise RuntimeError("Process handle not opened")
        old = ctypes.c_ulong(0)
        ok = kernel32.VirtualProtectEx(
            self.handle,
            ctypes.c_void_p(address),
            size,
            new_protect,
            ctypes.byref(old),
        )
        if not ok:
            err = ctypes.get_last_error()
            raise OSError(f"VirtualProtectEx failed at {hex(address)}: error {err}")
        return old.value

    def allocate(self, size: int, protect: int = PAGE_READWRITE) -> int:
        if not self.handle:
            raise RuntimeError("Process handle not opened")
        addr = kernel32.VirtualAllocEx(
            self.handle, None, size, MEM_COMMIT | MEM_RESERVE, protect
        )
        if not addr:
            err = ctypes.get_last_error()
            raise OSError(f"VirtualAllocEx failed: error {err}")
        return addr

    def free(self, address: int) -> bool:
        return kernel32.VirtualFreeEx(self.handle, ctypes.c_void_p(address), 0, MEM_RELEASE) != 0

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc):
        self.close()
