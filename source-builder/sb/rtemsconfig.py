#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2013-2016 Chris Johns (chrisj@rtems.org)
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

from __future__ import print_function

import datetime
import operator
import os
import re
import sys
import threading
import time

from . import error
from . import log
from . import options
from . import path
from . import version


def _collect(path_, file):
    confs = []
    for root, dirs, files in os.walk(path.host(path_), topdown=True):
        for f in files:
            if f == file:
                confs += [path.shell(path.join(root, f))]
    return confs


def _grep(file, pattern):
    rege = re.compile(pattern)
    try:
        f = open(path.host(file), 'r')
        matches = [rege.match(l) != None for l in f.readlines()]
        f.close()
    except IOError as err:
        raise error.general('error reading: %s' % (file))
    return True in matches


class command:

    def __init__(self, opts, cmd, cwd=None):
        self.exit_code = 0
        self.output = None
        self.opts = opts
        self.cmd = cmd
        self.cwd = cwd

    def run(self):

        import subprocess

        #
        # Support Python 2.6
        #
        if "check_output" not in dir(subprocess):

            def f(*popenargs, **kwargs):
                if 'stdout' in kwargs:
                    raise ValueError(
                        'stdout argument not allowed, it will be overridden.')
                process = subprocess.Popen(stdout=subprocess.PIPE,
                                           *popenargs,
                                           **kwargs)
                output, unused_err = process.communicate()
                retcode = process.poll()
                if retcode:
                    cmd = kwargs.get("args")
                    if cmd is None:
                        cmd = popenargs[0]
                    raise subprocess.CalledProcessError(retcode, cmd)
                return output

            subprocess.check_output = f

        self.start_time = datetime.datetime.now()
        self.exit_code = 0
        try:
            cmd = [self.opts.defaults.expand(c) for c in self.cmd]
            self.output = subprocess.check_output(cmd, cwd=self.cwd)
        except subprocess.CalledProcessError as cpe:
            self.exit_code = cpe.returncode
            self.output = cpe.output
        self.end_time = datetime.datetime.now()


class bsp_config:

    filter_out = ['as', 'cc', 'ld', 'objcopy', 'size']

    def __init__(self, opts, prefix, arch_bsp):
        self.opts = opts
        self.prefix = prefix
        if not path.exists(prefix):
            raise error.general('RTEMS prefix path not found: %s' % (prefix))
        self.makefile_inc = None
        if '/' in arch_bsp:
            arch, bsp = arch_bsp.split('/', 1)
        else:
            arch = None
            bsp = arch_bsp
        makefile_incs = _collect(prefix, 'Makefile.inc')
        for mi in makefile_incs:
            found = True
            if arch is not None and arch not in mi:
                found = False
            if bsp not in mi:
                found = False
            if found:
                self.makefile_inc = mi
                break
        if self.makefile_inc is None:
            raise error.general('RTEMS BSP not found: %s' % (arch_bsp))
        if not path.exists(self.makefile_inc):
            raise error.general('RTEMS BSP configuration not found: %s: %s' % \
                                    (arch_bsp, self.makefile_inc))
        self.command = command(opts, [
            '%{__make}', '-f'
            '%{_sbdir}/sb/rtemsconfig.mk',
            'makefile_inc=%s' % (self.makefile_inc)
        ])
        self.command.run()
        self.parse(self.command.output)

    def __str__(self):
        s = None
        for c in sorted(self.configs.keys()):
            if s is None:
                s = ''
            else:
                s += os.linesep
            s += '%s = %s' % (c, self.configs[c])
        return s

    def parse(self, text):
        self.configs = {}
        lines = text.splitlines()
        lc = 0
        while lc < len(lines):
            l = lines[lc].strip()
            lc += 1
            if len(l) == 0 or l[0] == '#' or '=' not in l:
                continue
            key = l[:l.index('=')].strip()
            data = l[l.index('=') + 1:].strip()
            if len(data) == 0:
                continue
            if data[0] == '"':
                if len(data) == 1 or data[-1] != '"':
                    not_closed = True
                    while lc < len(lines) and not_closed:
                        l = lines[lc]
                        lc += 1
                        if l[-1] == '"':
                            data += l
                            not_close = False
            self.configs[key] = data

    def keys(self):
        _keys = {}
        for k in sorted(self.configs.keys()):
            _keys[k.lower()] = k
        return _keys

    def find(self, name):
        _keys = list(self.keys())
        nl = name.lower()
        if nl in _keys and not nl in bsp_config.filter_out:
            return self.configs[_keys[nl]]
        raise error.general('invalid configuration: %s' % (name))


def run(args):
    try:
        optargs = {
            '--rtems': 'The RTEMS source directory',
            '--rtems-bsp': 'The RTEMS BSP (arch/bsp)',
            '--list': 'List the configurations'
        }
        opts = options.load(sys.argv, optargs)

        if opts.get_arg('--rtems'):
            prefix = opts.get_arg('--rtems')[1]
        else:
            prefix = os.getcwd()
        if opts.get_arg('--rtems-bsp') is None:
            raise error.general('no --rtems-bsp option; please provide')

        bsp = bsp_config(opts, prefix, opts.get_arg('--rtems-bsp')[1])

        if opts.get_arg('--list'):
            log.notice('RTEMS Source Builder - RTEMS Configuration, %s' %
                       (version.string()))
            opts.log_info()
            configs = list(bsp.keys())
            for c in sorted(configs.keys()):
                print(c)
        else:
            for p in opts.params():
                print(bsp.find(p))

    except error.general as gerr:
        print(gerr)
        sys.exit(1)
    except error.internal as ierr:
        print(ierr)
        sys.exit(1)
    except error.exit as eerr:
        pass
    except KeyboardInterrupt:
        log.notice('abort: user terminated')
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    run(sys.argv)
