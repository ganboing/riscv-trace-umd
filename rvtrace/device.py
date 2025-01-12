"""
Copyright (C) 2025, Bo Gan <ganboing@gmail.com>

SPDX-License-Identifer: Apache 2.0
"""

import os
import sys
import mmap
import time
from rvtrace.iommap import mmap, PROT_READ, PROT_WRITE

DEVMEM = "/dev/mem"
TR_COMMON_CONTROL = 0x0
TR_COMMON_IMPL = 0x4
RESET_TIMEOUT = 1000 * 1000 * 1000
SINK_TYPES = ["Default",  "Reserved", "Reserved", "Reserved",
              "SRAM",     "ATB",      "PIB",      "SBA",
              "FUNNEL",   "Reserved", "Reserved", "Reserved",
              "Reserved", "Reserved", "Reserved", "Reserved", ]
SINK_TYPES_MAP = {
    "sram" : 4,
    "atb" : 5,
    "pib" : 6,
    "sba" : 7,
    "funnel" : 8
}

class DevMem(mmap):
    """
    Interface to /dev/mem
    """
    def __init__(self, size, offset=0, writable=False):
        fd = os.open(DEVMEM, os.O_RDWR if writable else os.O_RDONLY)
        prot = PROT_READ | (PROT_WRITE if writable else 0)
        super().__init__(fd, size, prot=prot, offset=offset)
        os.close(fd)

class Device:
    """
    Common for all trace components
    """
    def __init__(self, name, mmio_base, runtime):
        self.name = name
        self.mmio_base = mmio_base
        self.mmio = DevMem(0x1000, offset=mmio_base, writable=True)
        self.tr_impl = self.mmio.read32(TR_COMMON_IMPL)
        self.ver_major = self.tr_impl & 0xf
        self.ver_minor = self.tr_impl & 0xff >> 4
        if self.ver_major > 0:
            self.comp_type = self.tr_impl & 0xfff >> 8
        self.runtime = runtime

    def info(self):
        pass

    def reset(self):
        retry = 0
        self.control = 0
        start = time.monotonic_ns()
        while (self.control & 1) != 0:
            retry = retry + 1
            if time.monotonic_ns() - start > RESET_TIMEOUT:
                raise Exception(f'Timeout resetting {self.name}')
        self.control = 1
        start = time.monotonic_ns()
        while (self.control & 1) == 0:
            retry = retry + 1
            if time.monotonic_ns() - start > RESET_TIMEOUT:
                raise Exception(f'Timeout resetting {self.name}')
        print(f'Device {self.name} reset, control={self.control:0x} nread={retry}', file=sys.stderr)

    def probe(self):
        pass

    def config(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def dump(self, file, maxsize):
        pass
