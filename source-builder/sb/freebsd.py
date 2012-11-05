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

import execute

def load():
    uname = os.uname()
    sysctl = '/sbin/sysctl '
    e = execute.capture_execution()
    exit_code, proc, output = e.shell(sysctl + 'hw.ncpu')
    if exit_code == 0:
        smp_mflags = '-j' + output.split(' ')[1].strip()
    else:
        smp_mflags = ''
    if uname[4] == 'amd64':
        cpu = 'x86_64'
    else:
        cpu = uname[4]
    version = uname[2]
    if version.find('-') > 0:
        version = version.split('-')[0]
    defines = {
        '_os':          ('none',    'none',     'freebsd'),
        '_host':        ('triplet', 'required', cpu + '-freebsd' + version),
        '_host_vendor': ('none',    'none',     'pc'),
        '_host_os':     ('none',    'none',     'freebsd'),
        '_host_cpu':    ('none',    'none',     cpu),
        '_host_alias':  ('none',    'none',     '%{nil}'),
        '_host_arch':   ('none',    'none',     cpu),
        '_usr':         ('dir',     'required', '/usr/local'),
        '_var':         ('dir',     'optional', '/usr/local/var'),
        'optflags':     ('none',    'none',     '-O2 -I/usr/local/include -L/usr/local/lib'),
        '_smp_mflags':  ('none',    'none',     smp_mflags),
        '__bash':       ('exe',     'optional', '/usr/local//bin/bash'),
        '__xz':         ('exe',     'optional', '/usr/bin/xz'),
        '__make':       ('exe',     'required', 'gmake')
        }
    return defines

if __name__ == '__main__':
    pprint.pprint(load())
