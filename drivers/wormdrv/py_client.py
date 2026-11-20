# drivers/wormdrv/py_client.py — user-mode client للتواصل مع WormDrv عبر IOCTL.
# نطاق: تعليمي فقط، على نظامك، مع الحذر الكامل لقراءة/كتابة ذاكرة عملية أخرى.
import ctypes
import ctypes.wintypes as wt
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

GENERIC_READ_WRITE = 0xC0000000
FILE_DEVICE_UNKNOWN = 0x00000022
METHOD_BUFFERED = 0
FILE_ANY_ACCESS = 0

def CTL_CODE(dev, fun, method, access):
    return (dev << 16) | (access << 14) | (fun << 2) | method

IOCTL_WORM_OPEN  = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x8001, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_WORM_READ  = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x8002, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_WORM_WRITE = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x8003, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_WORM_CLOSE = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x8004, METHOD_BUFFERED, FILE_ANY_ACCESS)


class WORM_TARGET(ctypes.Structure):
    _fields_ = [("pid", ctypes.c_void_p),
                ("addr", ctypes.c_ulonglong),
                ("size", ctypes.c_ulonglong)]


class WormDrvClient:
    def __init__(self, device_path=r"\\.\WormDrv"):
        self.handle = ctypes.windll.kernel32.CreateFileW(
            ctypes.c_wchar_p(device_path), GENERIC_READ_WRITE, 0, None,
            ctypes.c_ulong(3), 0, None,
        )
        if self.handle == -1 or self.handle == 0xFFFFFFFFFFFFFFFF:
            raise OSError("لا يمكن فتح WormDrv — تأكد أن الخدمة تعمل: sc start WormDrv")

    def _ioctl(self, ioctl, payload: bytes, out_size: int = 0) -> bytes:
        buf = ctypes.create_string_buffer(payload, max(len(payload), out_size))
        ret = ctypes.c_ulong(0)
        ok = ctypes.windll.kernel32.DeviceIoControl(
            self.handle, ioctl, buf, len(payload), buf, max(len(payload), out_size),
            ctypes.byref(ret), None)
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
        return buf.raw[:ret.value]

    def open_target(self, pid: int) -> None:
        t = WORM_TARGET(ctypes.c_void_p(pid), 0, 0)
        self._ioctl(IOCTL_WORM_OPEN, bytes(t), 0)

    def read(self, addr: int, size: int) -> bytes:
        # buf = [WORM_TARGET header][output buffer]
        t = WORM_TARGET(None, addr, size)
        payload = bytes(t) + b"\x00" * size
        out = self._ioctl(IOCTL_WORM_READ, payload, size + 0x18)
        return out[0x18:0x18 + size]

    def write(self, addr: int, data: bytes) -> int:
        t = WORM_TARGET(None, addr, len(data))
        payload = bytes(t) + data
        self._ioctl(IOCTL_WORM_WRITE, payload, 0)
        return len(data)

    def close_target(self) -> None:
        self._ioctl(IOCTL_WORM_CLOSE, b"\x00" * 0x18, 0)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        ctypes.windll.kernel32.CloseHandle(self.handle)


if __name__ == "__main__":
    # مثال: اقرأ 64 بايت من 0x00007FF600000000 في عملية PID من command line
    if len(sys.argv) >= 3:
        pid = int(sys.argv[1]); addr = int(sys.argv[2], 16)
        with WormDrvClient() as c:
            c.open_target(pid)
            data = c.read(addr, 64)
            print(data.hex(" "))
            c.close_target()
    else:
        print("usage: python py_client.py <pid> <hex_addr>")
