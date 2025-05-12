"""
Copyright (C) 2025, Bo Gan <ganboing@gmail.com>

SPDX-License-Identifer: Apache 2.0
"""

import sys
import json
from os import path
from argparse import ArgumentParser
from rvtrace.topology import TraceTopology

BUILTIN_CFG = {
    'SiFive HiFive Premier P550' : 'p550.cfg'
}

def find_builtin_config():
    with open('/sys/firmware/devicetree/base/model', 'r', encoding='ascii') as f:
        model_txt = f.read().rstrip('\x00')
    cfg = BUILTIN_CFG.get(model_txt, None)
    if cfg is not None:
        return path.join(path.dirname(path.realpath(__file__)), f'platforms/{cfg}')
    raise Exception(f'failed to find builtin configuration for {model_txt}')

def cli_trace_info(topo):
    topo.info()

def cli_trace_reset(topo):
    topo.reset()

def cli_trace_probe(topo):
    topo.probe()

def cli_trace_config(topo):
    topo.config()

def cli_trace_timestamp(topo):
    topo.timestamp()

def cli_trace_tsdiff(topo, duration):
    topo.tsdiff(duration)

def cli_trace_start(topo):
    topo.start()

def cli_trace_stop(topo):
    topo.stop()

def cli_trace_itc(topo, channel, data, width, src=None):
    topo.itcsend(channel, int(data, 0), width, src)

def cli_trace_dump(topo, file, sink=None, maxsize=sys.maxsize):
    if file[0] == '-':
        topo.dump(sys.stdout.buffer, sink=sink, maxsize=maxsize)
        return
    with open(file[0], 'wb') as fp:
        topo.dump(fp, sink=sink, maxsize=maxsize)

def main():
    parser = ArgumentParser(prog='rvtrace')
    parser.add_argument('-c', '--config', dest='config')
    subparsers = parser.add_subparsers(help='subcommand help')

    sub_info = subparsers.add_parser('info', help='information on trace topology')
    sub_info.set_defaults(func=cli_trace_info)

    sub_reset = subparsers.add_parser('reset', help='reset trace topology')
    sub_reset.set_defaults(func=cli_trace_reset)

    sub_probe = subparsers.add_parser('probe', help='probe trace topology')
    sub_probe.set_defaults(func=cli_trace_probe)

    sub_config = subparsers.add_parser('config', help='configure trace topology')
    sub_config.set_defaults(func=cli_trace_config)

    sub_timestamp = subparsers.add_parser('timestamp', help='get timestamps of trace topology')
    sub_timestamp.set_defaults(func=cli_trace_timestamp)

    sub_tsdiff = subparsers.add_parser('tsdiff', help='get timestamp difference over a given duration')
    sub_tsdiff.add_argument('-d', dest='duration', type=int, default=1 * 1000 * 1000 * 1000,
                            help='Duration in seconds')
    sub_tsdiff.set_defaults(func=cli_trace_tsdiff)

    sub_start = subparsers.add_parser('start', help='start trace')
    sub_start.set_defaults(func=cli_trace_start)

    sub_stop = subparsers.add_parser('stop', help='stop trace')
    sub_stop.set_defaults(func=cli_trace_stop)

    sub_itc = subparsers.add_parser('itcsend', help='write ITC stimulus')
    sub_itc.add_argument('-s', '--src', dest='src', help='specify SRC encoder')
    sub_itc.add_argument('-c', '--channel', dest='channel', type=int, required=True, help='channel [0,32)')
    sub_itc.add_argument('-d', '--data', dest='data', required=True, help='data to send')
    sub_itc.add_argument('-w', '--width', dest='width', type=int, default=4, help='data width 1/2/4')
    sub_itc.set_defaults(func=cli_trace_itc)

    sub_dump = subparsers.add_parser('dump', help='dump trace buffer')
    sub_dump.add_argument('-s', '--sink', dest='sink', help='specify sink device')
    sub_dump.add_argument('-m', '--maxsize', dest='maxsize', type=int,
                          default=sys.maxsize, help='Maximum buffer to dump')
    sub_dump.add_argument('file', nargs=1)
    sub_dump.set_defaults(func=cli_trace_dump)

    options = parser.parse_args()
    func = vars(options).pop('func', None)
    if func is None:
        parser.print_help(sys.stderr)
        return

    config = vars(options).pop('config', None)
    if config is None:
        config = find_builtin_config()
    with open(config, 'r') as f:
        config = json.load(f)
    func(TraceTopology(config), **vars(options))