#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2013 Chris Johns (chrisj@rtems.org)
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

import error
import pprint
import os

import execute

def load():
    # Default to the native Windows Python.
    uname = 'win32'
    if os.environ.has_key('PROCESSOR_ARCHITECTURE'):
        if os.environ['PROCESSOR_ARCHITECTURE'] == 'AMD64':
            hosttype = 'x86_64'
            machsize = '64'
        else:
            hosttype = 'i686'
            machsize = '32'
    else:
        hosttype = 'x86_64'
        machsize = '32'

    # See if this is actually Cygwin Python
    if os.name == 'posix':
        try:
            uname = os.uname()
            hosttype = uname[4]
            uname = uname[0]
            if uname.startswith('CYGWIN'):
                uname = 'cygwin'
                host_triple = hosttype + '-pc-' + uname
                build_triple = hosttype + '-pc-' + uname
            else:
                raise error.general('invalid POSIX python')
        except:
            pass
    else:
        host_triple = '%s-w%s-mingw32' % (hosttype, machsize)
        build_triple = '%s-w%s-mingw32' % (hosttype, machsize)

    if os.environ.has_key('NUMBER_OF_PROCESSORS'):
        ncpus = os.environ['NUMBER_OF_PROCESSORS']
    else:
        ncpus = '1'

    if os.environ.has_key('MSYSTEM'):
        os.environ.pop('NUMBER_OF_PROCESSORS')

    version = uname[2]
    defines = {
        '_ncpus':            ('none',    'none',     ncpus),
        '_os':               ('none',    'none',     'win32'),
        '_build':            ('triplet', 'required', build_triple),
        '_build_vendor':     ('none',    'none',     'microsoft'),
        '_build_os':         ('none',    'none',     'win32'),
        '_build_os_version': ('none',    'none',     version),
        '_build_cpu':        ('none',    'none',     hosttype),
        '_build_alias':      ('none',    'none',     '%{nil}'),
        '_build_arch':       ('none',    'none',     hosttype),
        '_host':             ('triplet', 'required', host_triple),
        '_host_vendor':      ('none',    'none',     'microsoft'),
        '_host_os':          ('none',    'none',     'win32'),
        '_host_cpu':         ('none',    'none',     hosttype),
        '_host_alias':       ('none',    'none',     '%{nil}'),
        '_host_arch':        ('none',    'none',     hosttype),
        '_usr':              ('dir',     'optional', '/opt/local'),
        '_var':              ('dir',     'optional', '/opt/local/var'),
        '__bash':            ('exe',     'required', 'bash'),
        '__bzip2':           ('exe',     'required', 'bzip2'),
        '__bison':           ('exe',     'required', 'bison'),
        '__cat':             ('exe',     'required', 'cat'),
        '__cc':              ('exe',     'required', 'gcc'),
        '__chgrp':           ('exe',     'required', 'chgrp'),
        '__chmod':           ('exe',     'required', 'chmod'),
        '__chown':           ('exe',     'required', 'chown'),
        '__cp':              ('exe',     'required', 'cp'),
        '__cvs':             ('exe',     'required', 'cvs'),
        '__cxx':             ('exe',     'required', 'g++'),
        '__flex':            ('exe',     'required', 'flex'),
        '__git':             ('exe',     'required', 'git'),
        '__grep':            ('exe',     'required', 'grep'),
        '__gzip':            ('exe',     'required', 'gzip'),
        '__id':              ('exe',     'required', 'id'),
        '__install':         ('exe',     'required', 'install'),
        '__install_info':    ('exe',     'required', 'install-info'),
        '__ld':              ('exe',     'required', 'ld'),
        '__ldconfig':        ('exe',     'none',     ''),
        '__makeinfo':        ('exe',     'required', 'makeinfo'),
        '__mkdir':           ('exe',     'required', 'mkdir'),
        '__mv':              ('exe',     'required', 'mv'),
        '__nm':              ('exe',     'required', 'nm'),
        '__nm':              ('exe',     'required', 'nm'),
        '__objcopy':         ('exe',     'required', 'objcopy'),
        '__objdump':         ('exe',     'required', 'objdump'),
        '__patch':           ('exe',     'required', 'patch'),
        '__patch_bin':       ('exe',     'required', 'patch'),
        '__rm':              ('exe',     'required', 'rm'),
        '__sed':             ('exe',     'required', 'sed'),
        '__sh':              ('exe',     'required', 'sh'),
        '__tar':             ('exe',     'required', 'bsdtar'),
        '__touch':           ('exe',     'required', 'touch'),
        '__unzip':           ('exe',     'required', 'unzip'),
        '__xz':              ('exe',     'required', 'xz'),
        '_buildshell':       ('exe',     'required', '%{__sh}'),
        '___setup_shell':    ('exe',     'required', '%{__sh}')
        }
    return defines

if __name__ == '__main__':
    pprint.pprint(load())
