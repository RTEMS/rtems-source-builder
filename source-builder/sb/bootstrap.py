#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2013 Chris Johns (chrisj@rtems.org)
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

import datetime
import operator
import os
import re
import sys
import threading
import time

import error
import log
import options
import path
import version

def _collect(path_, file):
    confs = []
    for root, dirs, files in os.walk(path.host(path_), topdown = True):
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
    except IOError, err:
        raise error.general('reading: %s' % (file))
    return True in matches

class command:

    def __init__(self, cmd, cwd):
        self.exit_code = 0
        self.thread = None
        self.output = None
        self.cmd = cmd
        self.cwd = cwd
        self.result = None

    def runner(self):

        import subprocess

        #
        # Support Python 2.6
        #
        if "check_output" not in dir(subprocess):
            def f(*popenargs, **kwargs):
                if 'stdout' in kwargs:
                    raise ValueError('stdout argument not allowed, it will be overridden.')
                process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
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
            try:
                self.output = subprocess.check_output(self.cmd, cwd = self.cwd)
            except subprocess.CalledProcessError, cpe:
                self.exit_code = cpe.returncode
                self.output = cpe.output
            except OSError, ose:
                raise error.general('bootstrap failed: %s in %s: %s' % \
                                        (' '.join(self.cmd), self.cwd, (str(ose))))
            except KeyboardInterrupt:
                pass
            except:
                raise
        except:
            self.result = sys.exc_info()
        self.end_time = datetime.datetime.now()

    def run(self):
        self.thread = threading.Thread(target = self.runner)
        self.thread.start()

    def is_alive(self):
        return self.thread and self.thread.is_alive()

    def reraise(self):
        if self.result is not None:
            raise self.result[0], self.result[1], self.result[2]

class autoreconf:

    def __init__(self, topdir, configure):
        self.topdir = topdir
        self.configure = configure
        self.cwd = path.dirname(self.configure)
        self.bspopts()
        self.command = command(['autoreconf', '-i', '--no-recursive'], self.cwd)
        self.command.run()

    def bspopts(self):
        if _grep(self.configure, 'RTEMS_CHECK_BSPDIR'):
            bsp_specs = _collect(self.cwd, 'bsp_specs')
            try:
                acinclude = path.join(self.cwd, 'acinclude.m4')
                b = open(path.host(acinclude), 'w')
                b.write('# RTEMS_CHECK_BSPDIR(RTEMS_BSP_FAMILY)' + os.linesep)
                b.write('AC_DEFUN([RTEMS_CHECK_BSPDIR],' + os.linesep)
                b.write('[' + os.linesep)
                b.write('  case "$1" in' + os.linesep)
                for bs in sorted(bsp_specs):
                    dir = path.dirname(bs)[len(self.cwd) + 1:]
                    b.write('  %s )%s' % (dir, os.linesep))
                    b.write('    AC_CONFIG_SUBDIRS([%s]);;%s' % (dir, os.linesep))
                b.write('  *)' + os.linesep)
                b.write('    AC_MSG_ERROR([Invalid BSP]);;' + os.linesep)
                b.write('  esac' + os.linesep)
                b.write('])' + os.linesep)
                b.close()
            except IOError, err:
                raise error.general('writing: %s' % (acinclude))

    def is_alive(self):
        return self.command.is_alive()

    def post_process(self):
        if self.command is not None:
            self.command.reraise()
            if self.command.exit_code != 0:
                raise error.general('error: autoreconf: %s' % (' '.join(self.command.cmd)))
            makefile = path.join(self.cwd, 'Makefile.am')
            if path.exists(makefile):
                if _grep(makefile, 'stamp-h\.in'):
                    stamp_h = path.join(self.cwd, 'stamp-h.in')
                    try:
                        t = open(path.host(stamp_h), 'w')
                        t.write('timestamp')
                        t.close()
                    except IOError, err:
                        raise error.general('writing: %s' % (stamp_h))

def generate(topdir, jobs):
    if type(jobs) is str:
        jobs = int(jobs)
    start_time = datetime.datetime.now()
    confs = _collect(topdir, 'configure.ac')
    next = 0
    autoreconfs = []
    while next < len(confs) or len(autoreconfs) > 0:
        if next < len(confs) and len(autoreconfs) < jobs:
            log.notice('%3d/%3d: autoreconf: %s' % \
                           (next + 1, len(confs), confs[next][len(topdir) + 1:]))
            autoreconfs += [autoreconf(topdir, confs[next])]
            next += 1
        else:
            for ac in autoreconfs:
                if not ac.is_alive():
                    ac.post_process()
                    autoreconfs.remove(ac)
                    del ac
            if len(autoreconfs) >= jobs:
                time.sleep(1)
    end_time = datetime.datetime.now()
    log.notice('Bootstrap time: %s' % (str(end_time - start_time)))

class ampolish3:

    def __init__(self, topdir, makefile):
        self.topdir = topdir
        self.makefile = makefile
        self.preinstall = path.join(path.dirname(makefile), 'preinstall.am')
        self.command = command([path.join(topdir, 'ampolish3'), makefile], self.topdir)
        self.command.run()

    def is_alive(self):
        return self.command.is_alive()

    def post_process(self):
        if self.command is not None:
            if self.command.exit_code != 0:
                raise error.general('error: ampolish3: %s' % (' '.join(self.command.cmd)))
            try:
                p = open(path.host(self.preinstall), 'w')
                for l in self.command.output:
                    p.write(l)
                p.close()
            except IOError, err:
                raise error.general('writing: %s' % (self.preinstall))

def preinstall(topdir, jobs):
    if type(jobs) is str:
        jobs = int(jobs)
    start_time = datetime.datetime.now()
    makes = []
    for am in _collect(topdir, 'Makefile.am'):
        if _grep(am, 'include .*/preinstall\.am'):
            makes += [am]
    next = 0
    ampolish3s = []
    while next < len(makes) or len(ampolish3s) > 0:
        if next < len(makes) and len(ampolish3s) < jobs:
            log.notice('%3d/%3d: ampolish3: %s' % \
                           (next + 1, len(makes), makes[next][len(topdir) + 1:]))
            ampolish3s += [ampolish3(topdir, makes[next])]
            next += 1
        else:
            for ap in ampolish3s:
                if not ap.is_alive():
                    ap.post_process()
                    ampolish3s.remove(ap)
                    del ap
            if len(ampolish3s) >= jobs:
                time.sleep(1)
    end_time = datetime.datetime.now()
    log.notice('Preinstall time: %s' % (str(end_time - start_time)))

def run(args):
    try:
        optargs = { '--rtems':       'The RTEMS source directory',
                    '--preinstall':  'Preinstall AM generation' }
        log.notice('RTEMS Source Builder - RTEMS Bootstrap, v%s' % (version.str()))
        opts = options.load(sys.argv, optargs)
        if opts.get_arg('--rtems'):
            topdir = opts.get_arg('--rtems')
        else:
            topdir = os.getcwd()
        if opts.get_arg('--preinstall'):
            preinstall(topdir, opts.jobs(opts.defaults['_ncpus']))
        else:
            generate(topdir, opts.jobs(opts.defaults['_ncpus']))
    except error.general, gerr:
        print gerr
        print >> sys.stderr, 'Bootstrap FAILED'
        sys.exit(1)
    except error.internal, ierr:
        print ierr
        print >> sys.stderr, 'Bootstrap FAILED'
        sys.exit(1)
    except error.exit, eerr:
        pass
    except KeyboardInterrupt:
        log.notice('abort: user terminated')
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    run(sys.argv)
