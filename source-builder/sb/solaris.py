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
    psrinfo = '/sbin/psrinfo|wc -l'
    e = execute.capture_execution()
    exit_code, proc, output = e.shell(psrinfo)
    if exit_code == 0:
        ncpus = output
    else:
        ncpus = '1'
    if uname[4] == 'i86pc':
        cpu = 'i386'
    else:
        cpu = uname[4]
    version = uname[2]
    if version.find('-') > 0:
        version = version.split('-')[0]
    defines = {
        '_ncpus':           ('none',    'none',     ncpus),
        '_os':              ('none',    'none',     'solaris'),
        '_host':            ('triplet', 'required', cpu + '-pc-solaris2'),
        '_host_vendor':     ('none',    'none',     'pc'),
        '_host_os':         ('none',    'none',     'solaris'),
        '_host_os_version': ('none',    'none',     version),
        '_host_cpu':        ('none',    'none',     cpu),
        '_host_alias':      ('none',    'none',     '%{nil}'),
        '_host_arch':       ('none',    'none',     cpu),
        '_usr':             ('dir',     'required', '/usr'),
        '_var':             ('dir',     'optional', '/var'),
        '__bash':           ('exe',     'optional', '/usr/bin/bash'),
        '__bison':          ('exe',     'required', '/usr/bin/bison'),
        '__git':            ('exe',     'required', '/usr/bin/git'),
        '__svn':            ('exe',     'required', '/usr/bin/svn'),
        '__cvs':            ('exe',     'required', '/usr/bin/cvs'),
        '__xz':             ('exe',     'optional', '/usr/bin/xz'),
        '__make':           ('exe',     'required', 'gmake'),
        '__patch_opts':     ('none',     'none',    '-E'),
        '__chown':          ('exe',     'required', '/usr/bin/chown'),
        '__install':        ('exe',     'required', '/usr/bin/ginstall'),
        '__cc':             ('exe',     'required', '/usr/bin/gcc'),
        '__cxx':            ('exe',     'required', '/usr/bin/g++'),
        'with_iconv':       ('none',    'none',     '0')
        }

    defines['_build']        = defines['_host']
    defines['_build_vendor'] = defines['_host_vendor']
    defines['_build_os']     = defines['_host_os']
    defines['_build_cpu']    = defines['_host_cpu']
    defines['_build_alias']  = defines['_host_alias']
    defines['_build_arch']   = defines['_host_arch']

    return defines

if __name__ == '__main__':
    pprint.pprint(load())
