"""
Copyright (C) 2025, Bo Gan <ganboing@gmail.com>

SPDX-License-Identifer: Apache 2.0
"""

import ctypes
import os

from rvtrace.device import Device, SINK_TYPES, SINK_TYPES_MAP
from rvtrace.timestamp import Timestamp
from rvtrace.helper import get_pmem_range, send_file

TR_TF_CONTROL = 0x0
TR_TF_IMPL = 0x4
TR_TF_SINK_BASE = 0x10
TR_TF_SINK_BASE_HIGH = 0x14
TR_TF_SINK_LIMIT = 0x18
TR_TF_SINK_WP = 0x1c
TR_TF_TS_CONTROL = 0x40
TR_TF_TS_LOW = 0x44
TR_TF_TS_UPPER = 0x48

class TfControlV0Bits(ctypes.LittleEndianStructure):
    _fields_ = [
        ("tfActive",     ctypes.c_uint32, 1), # TF Master Enable/Reset
        ("tfEnable",     ctypes.c_uint32, 1), # TF Enable (SW controlled)
        ("reserved1",    ctypes.c_uint32, 1),
        ("tfEmpty",      ctypes.c_uint32, 1), # TF has flushed all traces
        ("reserved2",    ctypes.c_uint32, 10),
        ("tfStopOnWrap", ctypes.c_uint32, 1), # Set tfEnable=0 on wrap
        ("reserved3",    ctypes.c_uint32, 12),
        ("tfSinkError",  ctypes.c_uint32, 1), # Set when TileLink error (write 1 to clear)
        ("tfSink",       ctypes.c_uint32, 4), # Sink type: 7: SBA (RAM)
    ]

class TfControlV0(ctypes.Union):
    _anonymous_ = ("bits",)
    _fields_ = [
        ("bits",  TfControlV0Bits),
        ("value", ctypes.c_uint32),
    ]

class TfImplV0Bits(ctypes.LittleEndianStructure):
    _fields_ = [
        ("tfVersion",       ctypes.c_uint32, 4), # TF version
        ("tfHasSRAMSink",   ctypes.c_uint32, 1), # TF has on-chip SRAM sink
        ("tfHasATBSink",    ctypes.c_uint32, 1), # TF has ATB sink
        ("tfHasPIBSink",    ctypes.c_uint32, 1), # TF has off-chip trace port via PIB
        ("tfHasSBASink",    ctypes.c_uint32, 1), # TF has on-chip bus master through Front Port
        ("tfHasFunnelSink", ctypes.c_uint32, 1), # TF feeds into a Trace Funnel
        ("reserved1",       ctypes.c_uint32, 7),
        ("tfSinkBytes",     ctypes.c_uint32, 2), # TF trace sink width
        ("reserved2",       ctypes.c_uint32, 14),
    ]

class TfImplV0(ctypes.Union):
    _anonymous_ = ("bits",)
    _fields_ = [
        ("bits",  TfImplV0Bits),
        ("value", ctypes.c_uint32),
    ]

class TraceFunnelV0(Device):
    """
    Pre-ratified version of Trace Funnel.
    (Basically Funnel + Sink in 1.0+)
    """

    @property
    def control(self):
        return self.mmio.read32(TR_TF_CONTROL)

    @control.setter
    def control(self, value):
        self.mmio.write32(TR_TF_CONTROL, value)

    @property
    def tscontrol(self):
        return self.mmio.read32(TR_TF_TS_CONTROL)

    @tscontrol.setter
    def tscontrol(self, value):
        self.mmio.write32(TR_TF_TS_CONTROL, value)

    @property
    def ts(self):
        return (self.mmio.read32(TR_TF_TS_UPPER) << 32) + self.mmio.read32(TR_TF_TS_LOW)

    @ts.setter
    def ts(self, value):
        self.mmio.write32(TR_TF_TS_LOW, value & 0xffffffff)
        self.mmio.write32(TR_TF_TS_UPPER, value >> 32)

    @property
    def impl(self):
        return self.mmio.read32(TR_TF_IMPL)

    @property
    def sinkbase(self):
        return (self.mmio.read32(TR_TF_SINK_BASE_HIGH) << 32) + self.mmio.read32(TR_TF_SINK_BASE)

    @sinkbase.setter
    def sinkbase(self, value):
        self.mmio.write32(TR_TF_SINK_BASE, value & 0xffffffff)
        self.mmio.write32(TR_TF_SINK_BASE_HIGH, value >> 32)

    @property
    def sinklimit(self):
        return (self.mmio.read32(TR_TF_SINK_BASE_HIGH) << 32) + self.mmio.read32(TR_TF_SINK_LIMIT)

    @sinklimit.setter
    def sinklimit(self, value):
        sink_base_high = self.mmio.read32(TR_TF_SINK_BASE_HIGH)
        if sink_base_high != (value >> 32):
            raise Exception(f'SinkLimitHigh {value >> 32:0x} must be equal to '\
                            f'SinkBaseHigh {sink_base_high:0x}')
        self.mmio.write32(TR_TF_SINK_LIMIT, value & 0xffffffff)

    @property
    def sinkwp(self):
        return (self.mmio.read32(TR_TF_SINK_BASE_HIGH) << 32) + self.mmio.read32(TR_TF_SINK_WP)

    @sinkwp.setter
    def sinkwp(self, value):
        sink_base_high = self.mmio.read32(TR_TF_SINK_BASE_HIGH)
        if sink_base_high != (value >> 32):
            raise Exception(f'SinkWPHigh {value >> 32:0x} must be equal to '\
                            f'SinkBaseHigh {sink_base_high:0x}')
        self.mmio.write32(TR_TF_SINK_WP, value & 0xffffffff)

    @staticmethod
    def str_control(control):
        c = TfControlV0(value=control)
        return f'active={c.tfActive} '\
               f'enable={c.tfEnable} '\
               f'empty={c.tfEmpty} '\
               f'stoponwrap={c.tfStopOnWrap} '\
               f'sinkerr={c.tfSinkError} '\
               f'sink={SINK_TYPES[c.tfSink]}'

    @staticmethod
    def str_impl(impl):
        c = TfImplV0(value=impl)
        sink_bytes = ['32-bit', '64-bit', '128-bit', '256-bit']
        return f'version={c.tfVersion} '\
               f'sram={c.tfHasSRAMSink} '\
               f'atb={c.tfHasATBSink} '\
               f'pib={c.tfHasPIBSink} '\
               f'sba={c.tfHasSBASink} '\
               f'funnel={c.tfHasFunnelSink} '\
               f'sinkbytes={sink_bytes[c.tfSinkBytes]}'

    def info(self):
        return f'\timpl: {TraceFunnelV0.str_impl(self.impl)}\n' \
               f'\tcontrol={TraceFunnelV0.str_control(self.control)}\n'\
               f'\tsinkbase={self.sinkbase:0x} '\
               f'sinklimit={self.sinklimit:0x} '\
               f'sinkwp={self.sinkwp:0x}\n'\
               f'\ttimestamp: {Timestamp.str_control(self.tscontrol)}'

    def reset(self):
        super().reset()
        Timestamp.reset(self)

    def probe(self):
        self.reset()
        orig_control = self.control
        supported_sinks = []
        for sink in range(0, 16):
            self.control = TfControlV0(tfActive=1, tfSink=sink).value
            if TfControlV0(value=self.control).tfSink == sink:
                supported_sinks.append(sink)
        self.control = orig_control
        return f'sinks={supported_sinks}'\
               f'\n\ttimstamp: {Timestamp.probe(self)}'

    def config(self):
        enabled = self.runtime.get('enabled', False)
        if not enabled:
            self.control = 0
            return
        #self.control = TfControlV0(tfActive=0).value
        stoponwrap = self.runtime.get('stoponwrap', False)
        output = self.runtime.get('output', None)
        if output is not None and output not in SINK_TYPES_MAP:
            raise Exception(f'unknown output type {output}')
        if output in ['sram', 'sba']:
            pmem = self.runtime.get('pmem', None)
            if pmem is None:
                raise Exception(f'Do not know how to config sink {output}')
            pmem_base, pmem_size = get_pmem_range(pmem)
            if pmem_size == 0:
                raise Exception(f'pmem device {pmem} has zero size')
            align = 2 ** (TfImplV0(value=self.impl).tfSinkBytes + 2)
            if pmem_base % align != 0 or pmem_size % align != 0:
                raise Exception(f'pmem device {pmem} is not aligned to {align} bytes')
            pmem_limit = pmem_base + pmem_size - align
            self.sinkbase = pmem_base
            self.sinklimit = pmem_limit
            self.sinkwp = pmem_base
        self.control = TfControlV0(tfActive=1,
                                   tfStopOnWrap=1 if stoponwrap else 0,
                                   tfSink=0 if output is None else SINK_TYPES_MAP[output]).value
        if 'timestamp' in self.runtime:
            Timestamp.config(self, self.runtime['timestamp'])

    def start(self):
        if 'timestamp' in self.runtime:
            Timestamp.start(self)
        control = TfControlV0(value=self.control)
        control.tfEnable = 1
        control.tfSinkError = 1
        self.control = control.value

    def stop(self):
        control = TfControlV0(value=self.control)
        control.tfEnable = 0
        control.tfSinkError = 0
        self.control = control.value
        while TfControlV0(value=self.control).tfEmpty == 0:
            print(f'{self.name}: waiting for trace flush...')
        if 'timestamp' in self.runtime:
            Timestamp.stop(self)

    def dump(self, file, maxsize):
        control = TfControlV0(value=self.control)
        if control.tfEnable != 0:
            raise Exception(f"Funnel {self.name} must be stopped before dumping")
        output = self.runtime.get('output', None)
        if output not in ['sram', 'sba']:
            raise Exception(f'Funnel {self.name} must be configured in sram/sba mode')
        pmem = self.runtime.get('pmem', None)
        if pmem is None:
            raise Exception('No pmem device configured, unable to dump')
        sinkbase = self.sinkbase
        sinklimit = self.sinklimit
        sinkwp = self.sinkwp
        align = 2 ** (TfImplV0(value=self.impl).tfSinkBytes + 2)
        if sinkwp < sinkbase or sinkwp > sinklimit:
            raise Exception(f'sinkwp {sinkwp:0x} out of range [{sinkbase:0x},{sinklimit:0x}]')
        buffersize = sinklimit - sinkbase + align
        pos = (sinkwp & ~1) - sinkbase
        if pos % align != 0:
            raise Exception(f'pos {pos:0x} is not properly aligned to {align} bytes')
        maxsize = min(maxsize, buffersize)
        with open(f'/dev/{pmem}', 'rb') as pmemf:
            if (sinkwp & 1) == 0 or pos >= maxsize:
                size = min(pos, maxsize)
                send_file(file, pmemf, pos - size, size)
                return size
            # wrap around
            send_file(file, pmemf, buffersize - (maxsize - pos), maxsize - pos)
            send_file(file, pmemf, 0, pos)
            return maxsize
