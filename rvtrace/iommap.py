"""
Reimplementation of the standard Python mmap module with better control over access width,
to support memory-mapped I/O.

Copyright (C) ARM Ltd. 2019.  All rights reserved.
Copyright (C) 2025, Bo Gan <ganboing@gmail.com>

SPDX-License-Identifer: Apache 2.0
"""

import os
import ctypes
import errno
from importlib.machinery import EXTENSION_SUFFIXES
path = os.path

# Import the Python mmap module to get access to its constants.
import mmap as real_mmap
for x in real_mmap.__dict__:
    if x.startswith("PROT_") or x.startswith("MAP_"):
        globals()[x] = real_mmap.__dict__[x]
assert PROT_READ == real_mmap.PROT_READ
del real_mmap

libc = ctypes.CDLL(None, use_errno=True)
libc_mmap = libc.mmap
libc_mmap.restype = ctypes.c_void_p
libc_mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int,
                      ctypes.c_int, ctypes.c_int, ctypes.c_ulonglong]
libc_munmap = libc.munmap
libc_munmap.restype = ctypes.c_int
libc_munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]

def find_library(name):
    filedir = path.dirname(path.realpath(__file__))
    suffixes = [*EXTENSION_SUFFIXES]
    assert(len(suffixes) > 0)
    while True:
        try:
            extpath = path.join(filedir, f"../{name}{suffixes.pop(0)}")
            lib = ctypes.CDLL(extpath)
        except Exception as e:
            if len(suffixes) == 0:
                raise Exception(f"Cannot load {name}, last error: {e}")
            continue
        return lib

libmmio = find_library('libmmio')
for size in [8, 16, 32, 64]:
    func = getattr(libmmio, f'mmio_read{size}')
    globals()[f'libmmio_read{size}'] = func
    func.restype = getattr(ctypes, f'c_uint{size}')
    func.argtypes = [ctypes.c_void_p]
    func = getattr(libmmio, f'mmio_write{size}')
    globals()[f'libmmio_write{size}'] = func
    func.restype = ctypes.c_void_p
    func.argtypes = [ctypes.c_void_p, getattr(ctypes, f'c_uint{size}')]

class mmap:
    """
    Represent a single block of memory allocated by mmap.
    """
    def __init__(self, fno, size, flags=MAP_SHARED, prot=(PROT_WRITE|PROT_READ), offset=0):
        assert size > 0
        assert (size % os.sysconf("SC_PAGE_SIZE")) == 0
        assert offset >= 0
        self.size = size
        self.addr = libc_mmap(0, size, prot, flags, fno, offset)
        if (self.addr & 0xfff) == 0xfff:
            # Mapping failed. Possible reasons:
            #  - CONFIG_IO_STRICT_DEVMEM and area is forbidden
            if ctypes.get_errno() == errno.EPERM:
                raise PermissionError
            raise EnvironmentError

    def close(self):
        if libc_munmap(self.addr, self.size) != 0:
            raise OSError

    def read8(self, pos):
        return self.read(pos, 1)

    def read16(self, pos):
        return self.read(pos, 2)

    def read32(self, pos):
        return self.read(pos, 4)

    def read64(self, pos):
        return self.read(pos, 8)

    def read(self, start, nbytes):
        assert nbytes in [1,2,4,8], "invalid length for read: %u" % nbytes
        if nbytes == 1:
            return libmmio_read8(self.addr + start)
        elif nbytes == 2:
            return libmmio_read16(self.addr + start)
        elif nbytes == 4:
            return libmmio_read32(self.addr + start)
        elif nbytes == 8:
            return libmmio_read64(self.addr + start)
        else:
            assert False

    def write8(self, pos, value):
        return self.write(pos, 1, value)

    def write16(self, pos, value):
        return self.write(pos, 2, value)

    def write32(self, pos, value):
        return self.write(pos, 4, value)

    def write64(self, pos, value):
        return self.write(pos, 8, value)

    def write(self, start, nbytes, value):
        assert nbytes in [1,2,4,8], "invalid length for write: %u" % nbytes
        if nbytes == 1:
            libmmio_write8(self.addr + start, value)
        elif nbytes == 2:
            libmmio_write16(self.addr + start, value)
        elif nbytes == 4:
            libmmio_write32(self.addr + start, value)
        elif nbytes == 8:
            libmmio_write64(self.addr + start, value)
        else:
            assert False
