"""
Copyright (C) 2025, Bo Gan <ganboing@gmail.com>

SPDX-License-Identifer: Apache 2.0
"""

import sys
import time
import ctypes
from rvtrace.device import RESET_TIMEOUT

class TsControlBits(ctypes.LittleEndianStructure):
    _fields_ = [
        ("tsActive",    ctypes.c_uint32, 1), # TS Master Enable/Reset
        ("tsCount",     ctypes.c_uint32, 1), # TS Running (internal clk only)
        ("tsReset",     ctypes.c_uint32, 1), # Set 1 to reset timestamp (internal clk only)
        ("tsRunInDbg",  ctypes.c_uint32, 1), # TS Continues in Debug Mode (internal clk only)
        ("tsType",      ctypes.c_uint32, 3), # TS Type (RO)
        ("reserved1",   ctypes.c_uint32, 1),
        ("tsPrescale",  ctypes.c_uint32, 2), # Prescale timestamp by 2^(2*tsPrescale)
        ("reserved2",   ctypes.c_uint32, 5),
        ("tsEnable",    ctypes.c_uint32, 1), # TS/TE Enable timestamp in msg
        ("tsBranch",    ctypes.c_uint32, 2), # TS/TE Add timestamp field to branch messages
        ("tsITC",       ctypes.c_uint32, 1), # TS/TE Add timestamp field to Instrumentation messages
        ("tsOwnership", ctypes.c_uint32, 1), # TS/TE Add timestamp field to Ownership messages
        ("reserved3",   ctypes.c_uint32, 4),
        ("tsWidth",     ctypes.c_uint32, 6), # TS timestamp width
        ("reserved4",   ctypes.c_uint32, 2),
    ]

class TsControl(ctypes.Union):
    _anonymous_ = ("bits",)
    _fields_ = [
        ("bits",  TsControlBits),
        ("value", ctypes.c_uint32),
    ]

class Timestamp:
    @staticmethod
    def str_control(control):
        c = TsControl(value=control)
        types = ["None",  "External", "Internal-Bus", "Internal-Core",
                 "Slave", "Reserved", "Reserved",     "Reserved"]
        return f'active={c.tsActive} '\
               f'running={c.tsCount} '\
               f'type={types[c.tsType]} '\
               f'prescale={c.tsPrescale} '\
               f'msg={c.tsEnable} '\
               f'branch={c.tsBranch} '\
               f'itc={c.tsITC} '\
               f'ownership={c.tsOwnership} '\
               f'width={c.tsWidth}'

    @staticmethod
    def reset(device):
        device.tscontrol = 0
        device.tscontrol = 1
        start = time.monotonic_ns()
        retry = 0
        while (device.tscontrol & 1) == 0:
            if time.monotonic_ns() - start > RESET_TIMEOUT:
                raise Exception(f'Timeout resetting timstamp unit of {device.name}')
        print(f'Device {device.name} timestamp unit reset, nread={retry}', file=sys.stderr)

    @staticmethod
    def probe(device):
        orig_control = device.tscontrol
        ts_in_debug = False
        supported_types = []
        supported_branch_types = []
        support_itc = False
        support_ownership = False
        device.tscontrol = TsControl(tsActive=1, tsRunInDbg=1).value
        if TsControl(value=device.tscontrol).tsRunInDbg != 0:
            ts_in_debug = True
        for tstype in range(0, 8):
            device.tscontrol = TsControl(tsActive=1, tsType=tstype).value
            if TsControl(value=device.tscontrol).tsType == tstype:
                supported_types.append(tstype)
        for branch in range(0, 4):
            device.tscontrol = TsControl(tsActive=1, tsBranch=branch).value
            if TsControl(value=device.tscontrol).tsBranch == branch:
                supported_branch_types.append(branch)
        device.tscontrol = TsControl(tsActive=1, tsITC=1).value
        if TsControl(value=device.tscontrol).tsITC != 0:
            support_itc = True
        device.tscontrol = TsControl(tsActive=1, tsOwnership=1).value
        if TsControl(value=device.tscontrol).tsOwnership != 0:
            support_ownership = True
        device.tscontrol = orig_control
        return f'types={supported_types} '\
               f'runindebug={ts_in_debug} '\
               f'branchtypes={supported_branch_types} '\
               f'itc={support_itc} '\
               f'ownership={support_ownership}'

    @staticmethod
    def config(device, runtime, msgen=False):
        types_map = { 'external' : 1, 'bus' : 2, 'core' : 3, 'slave' : 4 }
        tstype = runtime.get('type', None)
        if tstype is None:
            raise Exception('timestamp type must be set')
        if tstype not in types_map:
            raise Exception(f'unknown timestamp type {tstype}')
        prescale = runtime.get('prescale', 0)
        branch = runtime.get('branch', 0)
        itc = runtime.get('itc', False)
        ownership = runtime.get('ownership', False)
        device.tscontrol = TsControl(tsActive=1,
                                     tsType=types_map[tstype],
                                     tsPrescale=prescale,
                                     tsEnable=1 if msgen else 0,
                                     tsBranch=branch,
                                     tsITC=1 if itc else 0,
                                     tsOwnership=1 if ownership else 0).value

    @staticmethod
    def start(device):
        control = TsControl(value=device.tscontrol)
        control.tsCount = 1
        device.tscontrol = control.value

    @staticmethod
    def stop(device):
        control = TsControl(value=device.tscontrol)
        control.tsCount = 0
        device.tscontrol = control.value
