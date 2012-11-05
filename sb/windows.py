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
# Windows specific support and overrides.
#

import pprint
import os

import execute

def load():
    uname = 'win32'
    if os.environ.has_key('NUMBER_OF_PROCESSORS'):
        ncpus = int(os.environ['NUMBER_OF_PROCESSORS'])
    else:
        ncpus = 0
    if ncpus > 1:
        smp_mflags = '-j' + str(ncpus)
    else:
        smp_mflags = ''
    if os.environ.has_key('HOSTTYPE'):
        hosttype = os.environ['HOSTTYPE']
    else:
        hosttype = 'i686'
    system = 'mingw32'
    defines = {
        '_os':            ('none',    'none',     'win32'),
        '_host':          ('triplet', 'required', hosttype + '-pc-' + system),
        '_host_vendor':   ('none',    'none',     'microsoft'),
        '_host_os':       ('none',    'none',     'win32'),
        '_host_cpu':      ('none',    'none',     hosttype),
        '_host_alias':    ('none',    'none',     '%{nil}'),
        '_host_arch':     ('none',    'none',     hosttype),
        '_usr':           ('dir',     'optional', '/opt/local'),
        '_var':           ('dir',     'optional', '/opt/local/var'),
        '_smp_mflags':    ('none',    'none',     smp_mflags),
        '__bash':         ('exe',     'required', 'bash'),
        '__bzip2':        ('exe',     'required', 'bzip2'),
        '__cat':          ('exe',     'required', 'cat'),
        '__cc':           ('exe',     'required', 'gcc'),
        '__chgrp':        ('exe',     'required', 'chgrp'),
        '__chmod':        ('exe',     'required', 'chmod'),
        '__chown':        ('exe',     'required', 'chown'),
        '__cp':           ('exe',     'required', 'cp'),
        '__cxx':          ('exe',     'required', 'g++'),
        '__grep':         ('exe',     'required', 'grep'),
        '__gzip':         ('exe',     'required', 'gzip'),
        '__id':           ('exe',     'required', 'id'),
        '__install':      ('exe',     'required', 'install'),
        '__install_info': ('exe',     'required', 'install-info'),
        '__ld':           ('exe',     'required', 'ld'),
        '__ldconfig':     ('exe',     'none',     ''),
        '__mkdir':        ('exe',     'required', 'mkdir'),
        '__mv':           ('exe',     'required', 'mv'),
        '__nm':           ('exe',     'required', 'nm'),
        '__nm':           ('exe',     'required', 'nm'),
        '__objcopy':      ('exe',     'required', 'objcopy'),
        '__objdump':      ('exe',     'required', 'objdump'),
        '__patch':        ('exe',     'required', 'patch'),
        '__rm':           ('exe',     'required', 'rm'),
        '__sed':          ('exe',     'required', 'sed'),
        '__sh':           ('exe',     'required', 'sh'),
        '__tar':          ('exe',     'required', 'bsdtar'),
        '__unzip':        ('exe',     'required', 'unzip'),
        '__xz':           ('exe',     'required', 'xz'),
        '_buildshell':    ('exe',     'required', '%{__sh}'),
        '___setup_shell': ('exe',     'required', '%{__sh}'),
        'optflags':       ('none',    'none',     '-O2 -pipe'),
        }
    return defines

if __name__ == '__main__':
    pprint.pprint(load())
