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

def load():
    uname = os.uname()
    sysctl = '/usr/sbin/sysctl '
    e = execute.capture_execution()
    exit_code, proc, output = e.shell(sysctl + 'hw.ncpu')
    if exit_code == 0:
        smp_mflags = '-j' + output.split(' ')[1].strip()
    else:
        smp_mflags = ''
    defines = {
        '_os':          ('none',    'none',     'darwin'),
        '_host':        ('triplet', 'required', uname[4] + '-apple-darwin' + uname[2]),
        '_host_vendor': ('none',    'none',     'apple'),
        '_host_os':     ('none',    'none',     'darwin'),
        '_host_cpu':    ('none',    'none',     uname[4]),
        '_host_alias':  ('none',    'none',     '%{nil}'),
        '_host_arch':   ('none',    'none',     uname[4]),
        '_usr':         ('dir',     'optionsl', '/opt/local'),
        '_var':         ('dir',     'optional', '/opt/local/var'),
        'optflags':     ('none',    'none',     '-O2'),
        '_smp_mflags':  ('none',    'none',     smp_mflags),
        '__xz':         ('exe',     'required', '/usr/local/bin/xz'),
        'with_zlib':    ('none',    'none',     '--with-zlib=no')
        }
    return defines

if __name__ == '__main__':
    pprint.pprint(load())
