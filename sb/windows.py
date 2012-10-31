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
        '_os':                     'win32',
        '_host':                   hosttype + '-pc-' + system,
        '_host_vendor':            'microsoft',
        '_host_os':                'win32',
        '_host_cpu':               hosttype,
        '_host_alias':             '%{nil}',
        '_host_arch':              hosttype,
        '_usr':                    '/opt/local',
        '_var':                    '/opt/local/var',
        'optflags':                '-O2 -fasynchronous-unwind-tables',
        '_smp_mflags':             smp_mflags,
        '__sh':                    'sh',
        '_buildshell':             '%{__sh}',
        '___setup_shell':          '%{__sh}',
        # Build flags
        'optflags':                '-O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions --param=ssp-buffer-size=4 -mms-bitfields'
        }
    return defines

if __name__ == '__main__':
    pprint.pprint(load())
