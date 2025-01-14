# Usermode Driver for RISC-V Trace

This repo serves as a reference/test usermode driver for RISC-V trace components

## Install

Install the stable version:

```
sudo pip install rvtrace
```

Install the developer version:

```
sudo pip install git+https://github.com/ganboing/riscv-trace-umd
```

For newer Debian/Ubuntu platforms, use `--break-system-packages`

```
sudo pip install --break-system-packages rvtrace
```
or
```
sudo pip install --break-system-packages git+https://github.com/ganboing/riscv-trace-umd
```

## Usage

```
usage: rvtrace [-h] [-c CONFIG] {info,reset,probe,config,timestamp,start,stop,dump} ...

positional arguments:
  {info,reset,probe,config,timestamp,start,stop,dump}
                        subcommand help
    info                information on trace topology
    reset               reset trace topology
    probe               probe trace topology
    config              configure trace topology
    timestamp           get timestamps of trace topology
    start               start trace
    stop                stop trace
    dump                dump trace buffer

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
```

For known platforms such as HiFive Premier P550 (EIC7700X),
no custom configuration is required, otherwise, use `-c` to specify the config file.
Refer to [p550.cfg](./rvtrace/platforms/p550.cfg) for the p550 config file. Tailor it
to fit your platform.

### Collect traces
As simple as:
```
# With sudo if not running as root
$ rvtrace start
$ rvtrace stop
$ rvtrace dump <trace.bin>
```
### Decode traces
Use the [modified NexRv with SrcBits=2 support](https://github.com/ganboing/tg-nexus-trace/tree/dev-p550/refcode/c)
```
$ NexRv.exe -dump <trace.bin>
...
0x74 011101_00: TCODE[6]=29 (MSG #585) - IndirectBranchHistSync
0x24 001001_00: SrcBits[2]=0x1 SYNC[4]=0x2
0x41 010000_01: BTYPE[2]=0x0 ICNT[4]=0x4
0x2C 001011_00:
0xA0 101000_00:
0x04 000001_00:
0x00 000000_00:
0x00 000000_00:
0x05 000001_01: FADDR[36]=0x40001A0B
0x0D 000011_01: HIST[6]=0x3
0x3C 001111_00:
0x74 011101_00:
0xA0 101000_00:
0xA0 101000_00:
0xCC 110011_00:
0xFC 111111_00:
0x13 000100_11: TSTAMP[42]=0xF3A2874F
...
```
### Debug
```
# With sudo if not running as root
$ rvtrace info
hart0-encoder TraceEncoderV0 @100000:
	impl: version=0 sram=0 atb=0 pib=0 sba=0 funnel=1 sinkbytes=32-bit crossing_type=Rational srcid=0 srcbits=2 hartid=0
	control: active=1 enable=0 tracing=0 empty=1 inst_mode=7 itc_mode=3 stallovf=1 stallen=0 stoponwrap=0 nosrc=0 syncmaxbtm=11 syncmaxinst=10 nexusformat=1 sinkerr=0 sink=FUNNEL
	timestamp: active=1 running=0 type=Slave prescale=0 msg=1 branch=3 itc=1 ownership=1 width=40
	outputs=['sys-funnel']
...
sys-funnel TraceFunnelV0 @18000:
	impl: version=0 sram=0 atb=0 pib=0 sba=1 funnel=0 sinkbytes=64-bit
	control=active=1 enable=0 empty=1 stoponwrap=0 sinkerr=0 sink=SBA
	sinkbase=100000000 sinklimit=1fffffff8 sinkwp=10fd07cc8
	timestamp: active=1 running=0 type=Internal-Bus prescale=0 msg=0 branch=0 itc=0 ownership=0 width=40
	inputs=['hart0-encoder', 'hart1-encoder', 'hart2-encoder', 'hart3-encoder']
	outputs=[]
```
## Additional Resources
[Nexus Trace Specs](https://github.com/riscv-non-isa/tg-nexus-trace/blob/main/README.md)
