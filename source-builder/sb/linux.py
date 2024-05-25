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

import multiprocessing
import platform
import pprint
import os

from . import path
from . import log


def load():
    uname = os.uname()
    if uname[4].startswith('arm'):
        cpu = 'arm'
    else:
        cpu = uname[4]

    version = uname[2]
    defines = {
        '_ncpus': ('none', 'none', str(multiprocessing.cpu_count())),
        '_os': ('none', 'none', 'linux'),
        '_host': ('triplet', 'required', cpu + '-linux-gnu'),
        '_host_vendor': ('none', 'none', 'gnu'),
        '_host_os': ('none', 'none', 'linux'),
        '_host_os_version': ('none', 'none', version),
        '_host_cpu': ('none', 'none', cpu),
        '_host_alias': ('none', 'none', '%{nil}'),
        '_host_arch': ('none', 'none', cpu),
        '_usr': ('dir', 'required', '/usr'),
        '_var': ('dir', 'required', '/var'),
        '_prefix': ('dir', 'optional', '/opt'),
        '__bzip2': ('exe', 'required', '/usr/bin/bzip2'),
        '__gzip': ('exe', 'required', '/bin/gzip'),
        '__tar': ('exe', 'required', '/bin/tar')
    }

    # platform.dist() was removed in Python 3.8
    # The distro module (introduced in Python 3.6, back-ported to 2.6)
    # is preferred.
    distro = ''
    distro_like = ''
    distro_ver = 0

    variations = {
        'debian': {
            '__bzip2': ('exe', 'required', '/bin/bzip2'),
            '__chgrp': ('exe', 'required', '/bin/chgrp'),
            '__chown': ('exe', 'required', '/bin/chown'),
            '__grep': ('exe', 'required', '/bin/grep'),
            '__sed': ('exe', 'required', '/bin/sed')
        },
        'redhat': {
            '__bzip2': ('exe', 'required', '/bin/bzip2'),
            '__chgrp': ('exe', 'required', '/bin/chgrp'),
            '__chown': ('exe', 'required', '/bin/chown'),
            '__install_info': ('exe', 'required', '/sbin/install-info'),
            '__grep': ('exe', 'required', '/bin/grep'),
            '__sed': ('exe', 'required', '/bin/sed'),
            '__touch': ('exe', 'required', '/bin/touch')
        },
        'fedora': {
            '__chown': ('exe', 'required', '/usr/bin/chown'),
            '__install_info': ('exe', 'required', '/usr/sbin/install-info')
        },
        'arch': {
            '__gzip': ('exe', 'required', '/usr/bin/gzip'),
            '__chown': ('exe', 'required', '/usr/bin/chown')
        },
        'suse': {
            '__chgrp': ('exe', 'required', '/usr/bin/chgrp'),
            '__chown': ('exe', 'required', '/usr/sbin/chown')
        },
        'gentoo': {
            '__bzip2': ('exe', 'required', '/bin/bzip2'),
            '__chgrp': ('exe', 'required', '/bin/chgrp'),
            '__chown': ('exe', 'required', '/bin/chown'),
            '__gzip': ('exe', 'required', '/bin/gzip'),
            '__grep': ('exe', 'required', '/bin/grep'),
            '__sed': ('exe', 'required', '/bin/sed')
        },
    }

    try:
        import distro as distro_mod
        distro = distro_mod.id()
        distro_like = distro_mod.like()
        try:
            distro_ver = float(distro_mod.version())
        except ValueError:
            pass
    except:
        pass

    if distro == '' and hasattr(platform, 'dist'):
        distro = platform.dist()[0]
        try:
            distro_ver = float(platform.dist()[1])
        except ValueError:
            pass

    # Non LSB - last resort, try issue
    if distro == '':
        try:
            with open('/etc/issue') as f:
                issue = f.read().split(' ')
                distro = issue[0]
                distro_ver = float(issue[2])
        except:
            pass

    if distro:
        distro = distro.lower()
    if distro_like:
        distro_like = distro_like.lower().split(' ')[0]

    # Some additional distro aliases
    if distro in ['centos']:
        distro_like = 'redhat'
    elif distro in ['fedora']:
        if distro_ver < 17:
            distro_like = 'redhat'
    elif distro in ['ubuntu', 'mx', 'linuxmint']:
        distro_like = 'debian'

    if not (distro in variations) and (distro_like in variations):
        distro = distro_like
        # Versions don't carry over to likes; e.g. linuxmint 21.6 != debian 21.6.
        distro_ver = 0

    if distro in variations:
        for v in variations[distro]:
            if path.exists(variations[distro][v][2]):
                defines[v] = variations[distro][v]
    else:
        log.warning(
            'Unrecognized OS distro; assuming defaults for grep, sed, etc.')
        try:
            distro_mod
        except:
            log.warning(
                "The 'distro' package may fix this problem; try 'pip install distro'."
            )

    defines['_build'] = defines['_host']
    defines['_build_vendor'] = defines['_host_vendor']
    defines['_build_os'] = defines['_host_os']
    defines['_build_cpu'] = defines['_host_cpu']
    defines['_build_alias'] = defines['_host_alias']
    defines['_build_arch'] = defines['_host_arch']

    return defines


if __name__ == '__main__':
    pprint.pprint(load())
