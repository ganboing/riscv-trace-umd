"""
Copyright (C) 2025, Bo Gan <ganboing@gmail.com>

SPDX-License-Identifer: Apache 2.0
"""
import os
import re
import stat
from os import path, sendfile

PMEM_NS_PATH=re.compile(r'/ndbus(\d+)/region(\d+)/namespace(\d+)\.(\d+)$')

def get_pmem_range(pmem_dev):
    ns_dir = path.realpath(f'/sys/block/{pmem_dev}/device', strict=True)
    if PMEM_NS_PATH.search(ns_dir) is None:
        raise Exception(f'unexpected pmem device path {ns_dir}')
    region_dir = path.dirname(ns_dir)
    with open(path.join(region_dir, 'resource'), 'r', encoding='ascii') as f:
        resource_txt = f.read()
    with open(path.join(region_dir, 'size'), 'r', encoding='ascii') as f:
        size_txt = f.read()
    return int(resource_txt, 0), int(size_txt, 0)

def send_file(file_out, file_in, offset, size):
    statbuf = os.fstat(file_out.fileno())
    if stat.S_ISREG(statbuf.st_mode):
        file_out.truncate(statbuf.st_size + size)
    while size > 0:
        xfer = min(size, 2 ** 30) # At most 1G a time
        xfer = sendfile(file_out.fileno(), file_in.fileno(), offset, xfer)
        if xfer == 0:
            raise Exception(f'EOF when sendfile {file_in.name} -> {file_out.name}')
        size = size - xfer
        offset = offset + xfer