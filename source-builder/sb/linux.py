#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2012 Chris Johns (chrisj@rtems.org)
# All rights reserved.
#
# This file is part of the RTEMS Tools package in 'rtems-tools'.
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

#
# This code is based on what ever doco about spec files I could find and
# RTEMS project's spec files.
#

import pprint
import os

import execute
import path

def load():
    uname = os.uname()
    smp_mflags = ''
    processors = '/bin/grep processor /proc/cpuinfo'
    e = execute.capture_execution()
    exit_code, proc, output = e.shell(processors)
    if exit_code == 0:
        cpus = 0
        for l in output.split('\n'):
            count = l.split(':')[1].strip()
            if count > cpus:
                cpus = int(count)
        if cpus > 0:
            smp_mflags = '-j%d' % (cpus)
    defines = {
        '_os':          ('none',    'none',     'linux'),
        '_host':        ('triplet', 'required', uname[4] + '-linux-gnu'),
        '_host_vendor': ('none',    'none',     'gnu'),
        '_host_os':     ('none',    'none',     'linux'),
        '_host_cpu':    ('none',    'none',     uname[4]),
        '_host_alias':  ('none',    'none',     '%{nil}'),
        '_host_arch':   ('none',    'none',     uname[4]),
        '_usr':         ('dir',     'required', '/usr'),
        '_var':         ('dir',     'required', '/var'),
        'optflags':     ('none',    'none',     '-O2'),
        '_smp_mflags':  ('none',    'none',     smp_mflags),
        '__bzip2':      ('exe',     'required', '/usr/bin/bzip2'),
        '__gzip':       ('exe',     'required', '/bin/gzip'),
        '__tar':        ('exe',     'required', '/bin/tar')
        }
    variations = {
        '__bzip2':      ('exe',     'required', '/bin/bzip2'),
	'__chgrp':      ('exe',     'required', '/bin/chgrp'),
	'__chown':      ('exe',     'required', '/bin/chown'),
	'__grep':       ('exe',     'required', '/bin/grep'),
	'__sed':        ('exe',     'required', '/bin/sed')
        }
    for v in variations:
        if path.exists(variations[v][2]):
	    defines[v] = variations[u]
    return defines

if __name__ == '__main__':
    pprint.pprint(load())
