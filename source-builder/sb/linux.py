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

import platform
import execute
import path

def load():
    uname = os.uname()
    smp_mflags = ''
    processors = '/bin/grep processor /proc/cpuinfo'
    e = execute.capture_execution()
    exit_code, proc, output = e.shell(processors)
    ncpus = 0
    if exit_code == 0:
        try:
            for l in output.split('\n'):
                count = l.split(':')[1].strip()
                if int(count) > ncpus:
                    ncpus = int(count)
        except:
            pass
    ncpus = str(ncpus + 1)
    if uname[4].startswith('arm'):
        cpu = 'arm'
    else:
        cpu = uname[4]

    version = uname[2]
    defines = {
        '_ncpus':           ('none',    'none',     ncpus),
        '_os':              ('none',    'none',     'linux'),
        '_host':            ('triplet', 'required', cpu + '-linux-gnu'),
        '_host_vendor':     ('none',    'none',     'gnu'),
        '_host_os':         ('none',    'none',     'linux'),
        '_host_os_version': ('none',    'none',     version),
        '_host_cpu':        ('none',    'none',     cpu),
        '_host_alias':      ('none',    'none',     '%{nil}'),
        '_host_arch':       ('none',    'none',     cpu),
        '_usr':             ('dir',     'required', '/usr'),
        '_var':             ('dir',     'required', '/var'),
        '__bzip2':          ('exe',     'required', '/usr/bin/bzip2'),
        '__gzip':           ('exe',     'required', '/bin/gzip'),
        '__tar':            ('exe',     'required', '/bin/tar')
        }

    # Works for LSB distros
    try:
        distro = platform.dist()[0]
        distro_ver = float(platform.dist()[1])
    except ValueError:
        # Non LSB distro found, use failover"
        pass

    # Non LSB - fail over to issue
    if distro == '':
        try:
            issue = open('/etc/issue').read()
            distro = issue.split(' ')[0]
            distro_ver = float(issue.split(' ')[2])
        except:
            pass

    # Manage distro aliases
    if distro in ['centos']:
        distro = 'redhat'
    elif distro in ['fedora']:
        if distro_ver < 17:
            distro = 'redhat'
    elif distro in ['centos', 'fedora']:
        distro = 'redhat'
    elif distro in ['Ubuntu', 'ubuntu', 'LinuxMint', 'linuxmint']:
        distro = 'debian'
    elif distro in ['Arch']:
        distro = 'arch'
    elif distro in ['SuSE']:
        distro = 'suse'

    variations = {
        'debian' : { '__bzip2':        ('exe',     'required', '/bin/bzip2'),
                     '__chgrp':        ('exe',     'required', '/bin/chgrp'),
                     '__chown':        ('exe',     'required', '/bin/chown'),
                     '__grep':         ('exe',     'required', '/bin/grep'),
                     '__sed':          ('exe',     'required', '/bin/sed') },
        'redhat' : { '__bzip2':        ('exe',     'required', '/bin/bzip2'),
                     '__chgrp':        ('exe',     'required', '/bin/chgrp'),
                     '__chown':        ('exe',     'required', '/bin/chown'),
                     '__install_info': ('exe',     'required', '/sbin/install-info'),
                     '__grep':         ('exe',     'required', '/bin/grep'),
                     '__sed':          ('exe',     'required', '/bin/sed'),
                     '__touch':        ('exe',     'required', '/bin/touch') },
        'fedora' : { '__chown':        ('exe',     'required', '/usr/bin/chown'),
                     '__install_info': ('exe',     'required', '/usr/sbin/install-info') },
        'arch'   : { '__gzip':         ('exe',     'required', '/usr/bin/gzip'),
                     '__chown':        ('exe',     'required', '/usr/bin/chown') },
        'suse'   : { '__chgrp':        ('exe',     'required', '/usr/bin/chgrp'),
                     '__chown':        ('exe',     'required', '/usr/sbin/chown') },
        }

    if variations.has_key(distro):
        for v in variations[distro]:
            if path.exists(variations[distro][v][2]):
                defines[v] = variations[distro][v]

    defines['_build']        = defines['_host']
    defines['_build_vendor'] = defines['_host_vendor']
    defines['_build_os']     = defines['_host_os']
    defines['_build_cpu']    = defines['_host_cpu']
    defines['_build_alias']  = defines['_host_alias']
    defines['_build_arch']   = defines['_host_arch']

    return defines

if __name__ == '__main__':
    pprint.pprint(load())
