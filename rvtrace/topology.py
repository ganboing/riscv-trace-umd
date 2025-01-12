"""
Copyright (C) 2025, Bo Gan <ganboing@gmail.com>

SPDX-License-Identifer: Apache 2.0
"""

import sys
from rvtrace.encoder import TraceEncoderV0
from rvtrace.funnel import TraceFunnelV0

class TraceEncoderPad:
    def __init__(self, encoder):
        self.encoder = encoder
        self.outputs = []

    @property
    def device(self):
        return self.encoder

class TraceFunnelPad:
    def __init__(self, funnel):
        self.funnel = funnel
        self.outputs = []
        self.inputs = []

    @property
    def device(self):
        return self.funnel

class TraceSinkPad:
    def __init__(self, sink):
        self.sink = sink
        self.inputs = []

    @property
    def device(self):
        return self.sink

DEVICE_TYPES = {
    "riscv,encoder0" : (TraceEncoderV0, TraceEncoderPad),
    "riscv,funnel0" :  (TraceFunnelV0, TraceFunnelPad),
}

class TraceTopology:
    def __init__(self, config):
        self.devices = {}
        self.pads = {}
        self.encoders = []
        self.sinks = []
        for name, cfg in config.items():
            type = cfg.get('type', None)
            if type is None or type not in DEVICE_TYPES:
                raise Exception(f'type must be specified as {DEVICE_TYPES.keys()}')
            reg = cfg.get('reg', None)
            if reg is None:
                raise Exception('reg must be specified')
            device = DEVICE_TYPES[type][0](name=name,
                                           mmio_base=int(reg, 16),
                                           runtime=cfg.get('runtime', {}))
            self.devices[name] = device
            pad = DEVICE_TYPES[type][1](device)
            self.pads[name] = pad
        for name, cfg in config.items():
            pad = self.pads[name]
            outputs = cfg.get('outputs', [])
            for dev in outputs:
                if not hasattr(pad, 'outputs'):
                    raise Exception(f'device {name} should not have outputs')
                if dev not in self.pads:
                    raise Exception(f'output device {dev} not found')
                outpad = self.pads[dev]
                if not hasattr(outpad, 'inputs'):
                    raise Exception(f'device {name} does not have inputs')
                pad.outputs.append(outpad)
                outpad.inputs.append(pad)
        for pad in self.pads.values():
            if not hasattr(pad, 'inputs'):
                self.encoders.append(pad)
            if not hasattr(pad, 'outputs') or not pad.outputs:
                self.sinks.append(pad)

    @staticmethod
    def apply(pads, action):
        if not pads:
            return
        outputs = set()
        for pad in pads:
            action(pad)
            if hasattr(pad, 'outputs'):
                outputs.update(pad.outputs)
        TraceTopology.apply(outputs, action)

    @staticmethod
    def apply_reverse(pads, action):
        if not pads:
            return
        inputs = set()
        for pad in pads:
            action(pad)
            if hasattr(pad, 'inputs'):
                inputs.update(pad.inputs)
        TraceTopology.apply_reverse(inputs, action)

    @staticmethod
    def devprefix(device):
        return f'{device.name} {device.__class__.__name__} @{device.mmio_base:0x}:'

    def info(self, file=sys.stdout):
        def _info(pad):
            device = pad.device
            print(TraceTopology.devprefix(device), file=file)
            print(device.info(), file=file)
            if hasattr(pad, 'inputs'):
                print(f'\tinputs={[input.device.name for input in pad.inputs]}', file=file)
            if hasattr(pad, 'outputs'):
                print(f'\toutputs={[output.device.name for output in pad.outputs]}', file=file)
        TraceTopology.apply(self.encoders, _info)

    def reset(self):
        def _reset(pad):
            device = pad.device
            device.reset()
        TraceTopology.apply(self.encoders, _reset)

    def probe(self, file=sys.stdout):
        def _probe(pad):
            device = pad.device
            print(TraceTopology.devprefix(device), file=file)
            print(f'\t{device.probe()}', file=file)
        TraceTopology.apply(self.encoders, _probe)

    def config(self, file=sys.stdout):
        self.reset()
        def _config(pad):
            device = pad.device
            device.config()
            print(f'{TraceTopology.devprefix(device)} configured', file=file)
        TraceTopology.apply_reverse(self.sinks, _config)

    def timestamp(self, file=sys.stdout):
        def _timestamp(pad):
            device = pad.device
            print(f'{TraceTopology.devprefix(device)} TS={device.ts:016d}', file=file)
        TraceTopology.apply(self.encoders, _timestamp)

    def start(self):
        self.config()
        def _start(pad):
            device = pad.device
            device.start()
        TraceTopology.apply_reverse(self.sinks, _start)

    def stop(self):
        def _stop(pad):
            device = pad.device
            device.stop()
        TraceTopology.apply(self.encoders, _stop)

    def dump(self, fp, sink=None, maxsize=sys.maxsize):
        if sink is None and len(self.sinks) != 1:
            raise Exception('sink must be specified for topology with multiple sinks')
        sink = self.sinks[0] if sink is None else self.pads[sink]
        return sink.device.dump(fp, maxsize)