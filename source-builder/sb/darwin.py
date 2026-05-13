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

import os

from . import execute


def load():
    uname = os.uname()
    sysctl = '/usr/sbin/sysctl '
    e = execute.capture_execution()
    exit_code, proc, output = e.shell(sysctl + 'hw.ncpu')
    if exit_code == 0:
        ncpus = output.split(' ')[1].strip()
    else:
        ncpus = '1'
    version = uname[2]
    if version.find('.'):
        version = version.split('.')[0]
    defines = {
        '_ncpus': ('none', 'none', ncpus),
        '_os': ('none', 'none', 'darwin'),
        '_host':
        ('triplet', 'required', uname[4] + '-apple-darwin' + uname[2]),
        '_host_vendor': ('none', 'none', 'apple'),
        '_host_os': ('none', 'none', 'darwin'),
        '_host_os_version': ('none', 'none', version),
        '_host_cpu': ('none', 'none', uname[4]),
        '_host_alias': ('none', 'none', '%{nil}'),
        '_host_arch': ('none', 'none', uname[4]),
        '_usr': ('dir', 'optional', '/usr/local'),
        '_var': ('dir', 'optional', '/usr/local/var'),
        '_prefix': ('dir', 'optional', '%{_usr}'),
        '__ldconfig': ('exe', 'none', ''),
        '__cmake': ('exe', 'optional', 'cmake'),
        '__cvs': ('exe', 'optional', 'cvs'),
        '__xz': ('exe', 'required', 'xz'),
        'with_zlib': ('none', 'none', '--with-zlib=no'),
        '_forced_static': ('none', 'none', ''),
        '_ld_library_path': ('none', 'none', 'DYLD_LIBRARY_PATH')
    }

    if version.find('.'):
        version = version.split('.')[0]
        if int(version) >= 13:
            defines['__cc'] = ('exe', 'required', '/usr/bin/cc')
            defines['__cxx'] = ('exe', 'required', '/usr/bin/c++')
            defines['build_cflags'] = '-O2 -pipe -fbracket-depth=1024'
            defines['build_cxxflags'] = '-O2 -pipe -fbracket-depth=1024'

    defines['_build'] = defines['_host']
    defines['_build_vendor'] = defines['_host_vendor']
    defines['_build_os'] = defines['_host_os']
    defines['_build_cpu'] = defines['_host_cpu']
    defines['_build_alias'] = defines['_host_alias']
    defines['_build_arch'] = defines['_host_arch']

    return defines


if __name__ == '__main__':
    import pprint
    pprint.pprint(load())
