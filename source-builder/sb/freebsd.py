#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2014 Chris Johns (chrisj@rtems.org)
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

import check
import error
import execute

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
        '_ncpus':           ('none',    'none',     ncpus),
        '_os':              ('none',    'none',     'freebsd'),
        '_host':            ('triplet', 'required', cpu + '-freebsd' + version),
        '_host_vendor':     ('none',    'none',     'pc'),
        '_host_os':         ('none',    'none',     'freebsd'),
        '_host_os_version': ('none',    'none',     version),
        '_host_cpu':        ('none',    'none',     cpu),
        '_host_alias':      ('none',    'none',     '%{nil}'),
        '_host_arch':       ('none',    'none',     cpu),
        '_usr':             ('dir',     'required', '/usr/local'),
        '_var':             ('dir',     'optional', '/usr/local/var'),
        '__bash':           ('exe',     'optional', '/usr/local/bin/bash'),
        '__bison':          ('exe',     'required', '/usr/local/bin/bison'),
        '__git':            ('exe',     'required', '/usr/local/bin/git'),
        '__svn':            ('exe',     'required', '/usr/local/bin/svn'),
        '__xz':             ('exe',     'optional', '/usr/bin/xz'),
        '__make':           ('exe',     'required', 'gmake'),
        '__patch_opts':     ('none',     'none',    '-E')
        }

    defines['_build']        = defines['_host']
    defines['_build_vendor'] = defines['_host_vendor']
    defines['_build_os']     = defines['_host_os']
    defines['_build_cpu']    = defines['_host_cpu']
    defines['_build_alias']  = defines['_host_alias']
    defines['_build_arch']   = defines['_host_arch']

    # FreeBSD 10 and above no longer have /usr/bin/cvs, but it can (e.g.) be
    # installed to /usr/local/bin/cvs through the devel/cvs port
    if int(float(version)) >= 10:
        #
        # FreeBSD has switched to clang plus gcc. On 10.0 cc is gcc based and
        # clang is provided however it is not building binutils-2.24.
        #
        cc = '/usr/bin/cc'
        if check.check_exe(cc, cc):
            defines['__cc'] = cc
        else:
            cc = '/usr/bin/clang'
            if not check.check_exe(cc, cc):
                raise error.general('no valid cc found')
        cxx = '/usr/bin/c++'
        if check.check_exe(cxx, cxx):
            defines['__cxx'] = cxx
        else:
            cxx = '/usr/bin/clang++'
            if check.check_exe(cxx, cxx):
                raise error.general('no valid c++ found')
        #
        # Assume the compiler is clang and so we need to increase
        # bracket depth build build the gcc ARM compiler.
        #
        defines['build_cflags'] = '-O2 -pipe -fbracket-depth=1024'
        defines['build_cxxflags'] = '-O2 -pipe -fbracket-depth=1024'
        cvs = 'cvs'
        if check.check_exe(cvs, cvs):
            defines['__cvs'] = cvs
        #
        # Fix the mess iconv is on FreeBSD 10.0.
        #
        defines['iconv_includes'] = ('none', 'none', '-I/usr/local/include -L/usr/local/lib')
    else:
        for gv in ['49', '48', '47']:
            gcc = '%s-portbld-freebsd%s-gcc%s' % (cpu, version, gv)
            if check.check_exe(gcc, gcc):
                defines['__cc'] = gcc
                break
        for gv in ['49', '48', '47']:
            gxx = '%s-portbld-freebsd%s-g++%s' % (cpu, version, gv)
            if check.check_exe(gxx, gxx):
                defines['__cxx'] = gxx
                break

    return defines

if __name__ == '__main__':
    pprint.pprint(load())
