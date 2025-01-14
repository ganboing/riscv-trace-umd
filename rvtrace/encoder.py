"""
Copyright (C) 2025, Bo Gan <ganboing@gmail.com>

SPDX-License-Identifer: Apache 2.0
"""

import ctypes
from rvtrace.device import Device, SINK_TYPES, SINK_TYPES_MAP
from rvtrace.timestamp import Timestamp

TR_TE_CONTROL = 0x0
TR_TE_IMPL = 0x4
TR_TE_TS_CONTROL = 0x40
TR_TE_TS_LOW = 0x44
TR_TE_TS_UPPER = 0x48
TR_TE_ITC_TRACE_EN = 0x60
TR_TE_ITC_TRIG_EN = 0x64
TR_TE_ITC_BLOCK = 0x80

class TeControlV0Bits(ctypes.LittleEndianStructure):
    _fields_ = [
        ("teActive",      ctypes.c_uint32, 1), # TE Master Enable/Reset
        ("teEnable",      ctypes.c_uint32, 1), # TE Enable (SW controlled)
        ("teTracing",     ctypes.c_uint32, 1), # TE Tracing (SW/HW controlled)
        ("teEmpty",       ctypes.c_uint32, 1), # TE has flushed all traces
        ("teInstMode",    ctypes.c_uint32, 3), # Instruction tracing mode
        ("teITCMode",     ctypes.c_uint32, 2), # ITC trace generation parameters
        ("resreved1",     ctypes.c_uint32, 3),
        ("teStallOvf",    ctypes.c_uint32, 1), # Overflow/stall indicator (SW clearable)
        ("teStallEn",     ctypes.c_uint32, 1), # Force core stall by TE
        ("teStopOnWrap",  ctypes.c_uint32, 1), # Set teEnable=0 on wrap
        ("teInhibitSrc",  ctypes.c_uint32, 1), # Disable SRC field in Nexus msg
        ("teSyncMaxBTM",  ctypes.c_uint32, 4), # SYNC msg per 2^(teSyncMaxBTM+5) BTMs 0xf=OFF
        ("teSyncMaxInst", ctypes.c_uint32, 4), # SYNC msg per 2^(teSyncMaxInst+5) I-CNT 0xf=OFF
        ("teSliceFormat", ctypes.c_uint32, 3), # Set to 1: 6 MDO + 2 MSEO
        ("teSinkError",   ctypes.c_uint32, 1), # Set when sink refuses msgs (write 1 to clear)
        ("teSink",        ctypes.c_uint32, 4), # Sink type: 8: Funnel
    ]

class TeControlV0(ctypes.Union):
    _anonymous_ = ("bits",)
    _fields_ = [
        ("bits",  TeControlV0Bits),
        ("value", ctypes.c_uint32),
    ]

class TeImplV0Bits(ctypes.LittleEndianStructure):
    _fields_ = [
        ("teVersion",       ctypes.c_uint32, 4), # TE version
        ("teHasSRAMSink",   ctypes.c_uint32, 1), # TE has on-chip SRAM sink
        ("teHasATBSink",    ctypes.c_uint32, 1), # TE has ATB sink
        ("teHasPIBSink",    ctypes.c_uint32, 1), # TE has off-chip trace port via PIB
        ("teHasSBASink",    ctypes.c_uint32, 1), # TE has on-chip bus master through Front Port
        ("teHasFunnelSink", ctypes.c_uint32, 1), # TE feeds into a Trace Funnel
        ("reserved1",       ctypes.c_uint32, 7),
        ("teSinkBytes",     ctypes.c_uint32, 2), # TE trace sink width
        ("teCrossingType",  ctypes.c_uint32, 2), # TE clock crossing between ingress and BTM Gen
        ("teSrcID",         ctypes.c_uint32, 4), # TE source ID
        ("teNSrcBits",      ctypes.c_uint32, 3), # TE Nexus SRC field width
        ("reserved2",       ctypes.c_uint32, 1),
        ("teHartID",        ctypes.c_uint32, 4), # TE Hart ID
    ]

class TeImplV0(ctypes.Union):
    _anonymous_ = ("bits",)
    _fields_ = [
        ("bits",  TeImplV0Bits),
        ("value", ctypes.c_uint32),
    ]

class TraceEncoderV0(Device):
    """
    Pre-ratified version of Trace Encoder.
    """
    @property
    def control(self):
        return self.mmio.read32(TR_TE_CONTROL)

    @control.setter
    def control(self, value):
        self.mmio.write32(TR_TE_CONTROL, value)

    @property
    def tscontrol(self):
        return self.mmio.read32(TR_TE_TS_CONTROL)

    @tscontrol.setter
    def tscontrol(self, value):
        self.mmio.write32(TR_TE_TS_CONTROL, value)

    @property
    def ts(self):
        return (self.mmio.read32(TR_TE_TS_UPPER) << 32) + self.mmio.read32(TR_TE_TS_LOW)

    @ts.setter
    def ts(self, value):
        self.mmio.write32(TR_TE_TS_LOW, value & 0xffffffff)
        self.mmio.write32(TR_TE_TS_UPPER, value >> 32)

    @property
    def impl(self):
        return self.mmio.read32(TR_TE_IMPL)

    @staticmethod
    def str_control(control):
        c = TeControlV0(value=control)
        return f'active={c.teActive} '\
               f'enable={c.teEnable} '\
               f'tracing={c.teTracing} '\
               f'empty={c.teEmpty} '\
               f'inst_mode={c.teInstMode} '\
               f'itc_mode={c.teITCMode} '\
               f'stallovf={c.teStallOvf} '\
               f'stallen={c.teStallEn} '\
               f'stoponwrap={c.teStopOnWrap} '\
               f'nosrc={c.teInhibitSrc} '\
               f'syncmaxbtm={c.teSyncMaxBTM} '\
               f'syncmaxinst={c.teSyncMaxInst} '\
               f'nexusformat={c.teSliceFormat} '\
               f'sinkerr={c.teSinkError} '\
               f'sink={SINK_TYPES[c.teSink]}'

    @staticmethod
    def str_impl(impl):
        c = TeImplV0(value=impl)
        sink_bytes = ['32-bit', '64-bit', '128-bit', '256-bit']
        crossing_type = ['Synchronous', 'Rational', 'Asynchronous', 'Unknown']
        return f'version={c.teVersion} '\
               f'sram={c.teHasSRAMSink} '\
               f'atb={c.teHasATBSink} '\
               f'pib={c.teHasPIBSink} '\
               f'sba={c.teHasSBASink} '\
               f'funnel={c.teHasFunnelSink} '\
               f'sinkbytes={sink_bytes[c.teSinkBytes]} '\
               f'crossing_type={crossing_type[c.teCrossingType]} '\
               f'srcid={c.teSrcID} '\
               f'srcbits={c.teNSrcBits} '\
               f'hartid={c.teHartID}'

    def info(self):
        return f'\timpl: {TraceEncoderV0.str_impl(self.impl)}\n' \
               f'\tcontrol: {TraceEncoderV0.str_control(self.control)}\n'\
               f'\ttimestamp: {Timestamp.str_control(self.tscontrol)}'

    def reset(self):
        super().reset()
        Timestamp.reset(self)

    def probe(self):
        self.reset()
        orig_control = self.control
        supported_inst = []
        supported_itc = []
        supported_sync_maxbtm = []
        supported_sync_maxinst = []
        supported_sinks = []
        for inst_mode in range(0, 8):
            self.control = TeControlV0(teActive=1, teInstMode=inst_mode).value
            if TeControlV0(value=self.control).teInstMode == inst_mode:
                supported_inst.append(inst_mode)
        for itc_mode in range(0, 4):
            self.control = TeControlV0(teActive=1, teITCMode=itc_mode).value
            if TeControlV0(value=self.control).teITCMode == itc_mode:
                supported_itc.append(itc_mode)
        for sync_maxbtm in range(0, 16):
            self.control = TeControlV0(teActive=1, teSyncMaxBTM=sync_maxbtm).value
            if TeControlV0(value=self.control).teSyncMaxBTM == sync_maxbtm:
                supported_sync_maxbtm.append(sync_maxbtm)
        for sync_maxinst in range(0, 16):
            self.control = TeControlV0(teActive=1, teSyncMaxInst=sync_maxinst).value
            if TeControlV0(value=self.control).teSyncMaxInst == sync_maxinst:
                supported_sync_maxinst.append(sync_maxinst)
        for sink in range(0, 16):
            self.control = TeControlV0(teActive=1, teSink=sink).value
            if TeControlV0(value=self.control).teSink == sink:
                supported_sinks.append(sink)
        self.control = orig_control
        return f'instmode={supported_inst} '\
               f'itcmode={supported_itc} '\
               f'sync_maxbtm={supported_sync_maxbtm} '\
               f'sync_maxinst={supported_sync_maxinst} '\
               f'sinks={supported_sinks}'\
               f'\n\ttimstamp: {Timestamp.probe(self)}'

    def config(self):
        enabled = self.runtime.get('enabled', False)
        if not enabled:
            self.control = 0
            return
        instmode = self.runtime.get('instmode', 0)
        itcmode = self.runtime.get('itcmode', 0)
        stall = self.runtime.get('stall', False)
        stoponwrap = self.runtime.get('stoponwrap', False)
        syncmaxbtm = self.runtime.get('syncmaxbtm', 15)
        syncmaxinst = self.runtime.get('syncmaxinst', 15)
        output = self.runtime.get('output', None)
        if output is not None and output not in SINK_TYPES_MAP:
            raise Exception(f'unknown output type {output}')
        if output in ['sram', 'sba']:
            raise Exception(f'output type {output} is not supported for encoderv0')
        self.control = TeControlV0(teActive=1,
                                   teInstMode=instmode,
                                   teITCMode=itcmode,
                                   teStallEn=1 if stall else 0,
                                   teStopOnWrap=1 if stoponwrap else 0,
                                   teSyncMaxBTM=syncmaxbtm,
                                   teSyncMaxInst=syncmaxinst,
                                   teSink=0 if output is None else SINK_TYPES_MAP[output]).value
        if 'timestamp' in self.runtime:
            Timestamp.config(self, self.runtime['timestamp'], msgen=True)

    def start(self):
        if 'timestamp' in self.runtime:
            Timestamp.start(self)
        control = TeControlV0(value=self.control)
        control.teEnable = 1
        control.teTracing = 1
        control.teSinkError = 1
        self.control = control.value

    def stop(self):
        control = TeControlV0(value=self.control)
        control.teEnable = 0
        control.teSinkError = 0
        self.control = control.value
        while TeControlV0(value=self.control).teEmpty == 0:
            print(f'{self.name}: waiting for trace flush...')
        if 'timestamp' in self.runtime:
            Timestamp.stop(self)

    def dump(self, *args, **kwargs):
        control = TeControlV0(value=self.control)
        if control.teEnable != 0:
            raise Exception(f"Encoder {self.name} must be stopped before dumping")
        if self.runtime.get('output', None) != 'funnel':
            raise Exception("Only support funnel output of envoderv0")
        raise Exception(f"You should dump through funnel of Encoder {self.name}")
