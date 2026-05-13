#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2012 Chris Johns (chrisj@rtems.org)
# All rights reserved.
#
# This file is part of the RTEMS Tools package in 'rtems-tools'.
#
# RTEMS Tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RTEMS Tools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RTEMS Tools.  If not, see <http://www.gnu.org/licenses/>.
#

#
# This code is based on what ever doco about spec files I could find and
# RTEMS project's spec files.
#

import pprint
import os

from . import check
from . import execute


def load():
    uname = os.uname()
    sysctl = '/sbin/sysctl '
    e = execute.capture_execution()
    exit_code, proc, output = e.shell(sysctl + 'hw.ncpu')
    if exit_code == 0:
        ncpus = output.split(' ')[1].strip()
    else:
        ncpus = '1'
    if uname[4] == 'amd64':
        cpu = 'x86_64'
    else:
        cpu = uname[4]
    version = uname[2]
    if version.find('-') > 0:
        version = version.split('-')[0]
    defines = {
        '_ncpus': ('none', 'none', '1'),
        '_os': ('none', 'none', 'netbsd'),
        '_host': ('triplet', 'required', cpu + '-netbsd' + version),
        '_host_vendor': ('none', 'none', 'pc'),
        '_host_os': ('none', 'none', 'netbsd'),
        '_host_os_version': ('none', 'none', version),
        '_host_cpu': ('none', 'none', cpu),
        '_host_alias': ('none', 'none', '%{nil}'),
        '_host_arch': ('none', 'none', cpu),
        '_usr': ('dir', 'required', '/usr'),
        '_var': ('dir', 'optional', '/var'),
        'optincludes_build':
        ('none', 'none', '-I/usr/pkg/include -L/usr/pkg/lib'),
        '__bash': ('exe', 'optional', '/usr/pkg/bin/bash'),
        '__bison': ('exe', 'required', '/usr/pkg/bin/bison'),
        '__git': ('exe', 'required', '/usr/pkg/bin/git'),
        '__svn': ('exe', 'required', '/usr/pkg/bin/svn'),
        '__xz': ('exe', 'optional', '/usr/pkg/bin/xz'),
        '__make': ('exe', 'required', 'gmake'),
        '__patch_opts': ('none', 'none', '-E')
    }

    defines['_build'] = defines['_host']
    defines['_build_vendor'] = defines['_host_vendor']
    defines['_build_os'] = defines['_host_os']
    defines['_build_cpu'] = defines['_host_cpu']
    defines['_build_alias'] = defines['_host_alias']
    defines['_build_arch'] = defines['_host_arch']

    for gv in ['47', '48', '49']:
        gcc = '%s-portbld-netbsd%s-gcc%s' % (cpu, version, gv)
        if check.check_exe(gcc, gcc):
            defines['__cc'] = gcc
            break
    for gv in ['47', '48', '49']:
        gxx = '%s-portbld-netbsd%s-g++%s' % (cpu, version, gv)
        if check.check_exe(gxx, gxx):
            defines['__cxx'] = gxx
            break

    return defines


if __name__ == '__main__':
    pprint.pprint(load())
