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

import check
import execute

def load():
    uname = os.uname()
    sysctl = '/sbin/sysctl '
    e = execute.capture_execution()
    exit_code, proc, output = e.shell(sysctl + 'hw.ncpu')
    if exit_code == 0:
        ncpus = output.split('=')[1].strip()
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
        '_ncpus':            ('none',    'none',     ncpus),
        '_os':               ('none',    'none',     'openbsd'),
        '_host':             ('triplet', 'required', cpu + '-openbsd' + version),
        '_host_vendor':      ('none',    'none',     'pc'),
        '_host_os':          ('none',    'none',     'openbsd'),
        '_host_os_version':  ('none',    'none',     version),
        '_host_cpu':         ('none',    'none',     cpu),
        '_host_alias':       ('none',    'none',     '%{nil}'),
        '_host_arch':        ('none',    'none',     cpu),
        '_usr':              ('dir',     'required', '/usr'),
        '_var':              ('dir',     'optional', '/var'),
        'optincludes_build': ('none',    'none',     '-I/usr/local/include -L/usr/local/lib'),
        '__chgrp':           ('exe',     'required', '/bin/chgrp'),
        '__tar':             ('exe',     'required', '/bin/tar'),
        '__bash':            ('exe',     'optional', '/usr/local/bin/bash'),
        '__bison':           ('exe',     'required', '/usr/local/bin/bison'),
        '__git':             ('exe',     'required', '/usr/local/bin/git'),
        '__svn':             ('exe',     'required', '/usr/local/bin/svn'),
        '__xz':              ('exe',     'optional', '/usr/local/bin/xz'),
        '__bzip2':           ('exe',     'required', '/usr/local/bin/bzip2'),
        '__unzip':           ('exe',     'required', '/usr/local/bin/unzip'),
        '__make':            ('exe',     'required', 'gmake'),
        '__m4':              ('exe',     'required', '/usr/local/bin/gm4'),
        '__awk':             ('exe',     'required', '/usr/local/bin/gawk'),
        '__sed':             ('exe',     'required', '/usr/local/bin/gsed'),
        '__patch':           ('exe',     'required', '/usr/local/bin/gpatch'),
        '__python':          ('exe',     'required', '/usr/local/bin/python2.7'),
        '__patch_opts':      ('none',    'none',     '-E'),
        'with_iconv':        ('none',    'none',     '0'),
        'without_python':    ('none',    'none',     '1')
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
