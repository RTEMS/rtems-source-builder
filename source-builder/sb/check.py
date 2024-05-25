#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2016 Chris Johns (chrisj@rtems.org)
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
# Check the defaults for a specific host.
#

from __future__ import print_function

import fnmatch
import os
import re

from . import error
from . import execute
from . import log
from . import options
from . import path
from . import version


def _check_none(_opts, macro, value, constraint):
    return True


def _check_triplet(_opts, macro, value, constraint):
    return True


def _check_dir(_opts, macro, value, constraint, silent=False):
    if constraint != 'none' and not path.isdir(value):
        if constraint == 'required':
            if not silent:
                log.notice('error: dir: not found: (%s) %s' % (macro, value))
            return False
        if not silent and _opts.warn_all():
            log.notice('warning: dir: not found: (%s) %s' % (macro, value))
    return True


def _check_exe(_opts, macro, value, constraint, silent=False):

    if len(value) == 0 or constraint == 'none':
        return True

    orig_value = value

    if path.isabspath(value):
        if path.isfile(value):
            return True
        if os.name == 'nt':
            if path.isfile('%s.exe' % (value)):
                return True
        value = path.basename(value)
        absexe = True
    else:
        absexe = False

    paths = os.environ['PATH'].split(os.pathsep)

    if _check_paths(value, paths):
        if absexe:
            if not silent:
                log.notice(
                    'warning: exe: absolute exe found in path: (%s) %s' %
                    (macro, orig_value))
        return True

    if constraint == 'optional':
        if not silent:
            log.trace('warning: exe: optional exe not found: (%s) %s' %
                      (macro, orig_value))
        return True

    if not silent:
        log.notice('error: exe: not found: (%s) %s' % (macro, orig_value))
    return False


def _check_paths(name, paths):
    for p in paths:
        exe = path.join(p, name)
        if path.isfile(exe):
            return True
        if os.name == 'nt':
            if path.isfile('%s.exe' % (exe)):
                return True
    return False


def path_check(opts, silent=False):
    if 'PATH' in os.environ:
        paths = os.environ['PATH'].split(os.pathsep)
        for p in paths:
            try:
                if len(p.strip()) == 0:
                    if not silent:
                        log.notice(
                            'error: environment PATH contains an empty path')
                    return False
                elif not options.host_windows and (p.strip() == '.'
                                                   or p.strip() == '..'):
                    if not silent:
                        log.notice('error: environment PATH invalid path: %s' %
                                   (p))
                    return False
                elif not path.exists(p):
                    if not silent and opts.warn_all():
                        log.notice('warning: environment PATH not found: %s' %
                                   (p))
                elif not path.isdir(p):
                    if not silent and opts.warn_all():
                        log.notice(
                            'warning: environment PATH not a directory: %s' %
                            (p))
            except Exception as e:
                if not silent:
                    log.notice(
                        'warning: environment PATH suspicious path: %s' % (e))
    return True


def host_setup(opts):
    """ Basic sanity check. All executables and directories must exist."""

    if not path_check(opts):
        return False

    checks = {
        'none': _check_none,
        'triplet': _check_triplet,
        'dir': _check_dir,
        'exe': _check_exe
    }

    sane = True

    log.trace('--- check host set up : start"')
    for d in list(opts.defaults.keys()):
        try:
            (test, constraint, value) = opts.defaults.get(d)
        except:
            if opts.defaults.get(d) is None:
                raise error.general('invalid default: %s: not found' % (d))
            else:
                raise error.general('invalid default: %s [%r]' %
                                    (d, opts.defaults.get(d)))
        if test != 'none':
            value = opts.defaults.expand(value)
            if test not in checks:
                raise error.general('invalid check test: %s [%r]' %
                                    (test, opts.defaults.get(d)))
            ok = checks[test](opts, d, value, constraint)
            if ok:
                tag = ' '
            else:
                tag = '*'
            log.trace('%c %15s: %r -> "%s"' %
                      (tag, d, opts.defaults.get(d), value))
            if sane and not ok:
                sane = False
    log.trace('--- check host set up : end"')

    return sane


def check_exe(label, exe):
    return _check_exe(None, label, exe, None, True)


def check_orphans(opts):

    def _find_files(path, globs, excludes=[]):
        ff = []
        for root, dirs, files in os.walk(path, followlinks=True):
            for f in files:
                for g in globs:
                    if fnmatch.fnmatch(f, g) and f not in excludes:
                        ff += [os.path.join(root, f)]
        return sorted(ff)

    def _clean(line):
        line = line[0:-1]
        b = line.find('#')
        if b >= 0:
            line = line[1:b]
        return line.strip()

    def _find(name, opts):
        ename = opts.defaults.expand(name)
        if ':' in ename:
            paths = path.dirname(ename).split(':')
            name = path.basename(name)
        else:
            paths = opts.defaults.get_value('_configdir').split(':')
        for p in paths:
            n = path.join(opts.defaults.expand(p), name)
            if path.exists(n):
                return n
        return None

    paths = opts.defaults.get_value('_configdir').split(':')

    cfgs = {}
    for p in paths:
        ep = opts.defaults.expand(p)
        print('Scanning: %s (%s)' % (p, ep))
        for f in _find_files(ep, ['*.cfg', '*.bset']):
            root, ext = path.splitext(f)
            cfgs[f] = {'src': None, 'ext': ext, 'refs': 0, 'errors': []}

    wss = re.compile(r'\s+')

    for c in cfgs:
        with open(c, 'r') as f:
            cfgs[c]['src'] = f.readlines()
        lc = 0
        for l in cfgs[c]['src']:
            lc += 1
            l = _clean(l)
            if len(l) == 0:
                continue
            if l[0] == '%':
                ls = wss.split(l, 2)
                if ls[0] == '%include':
                    name = _find(ls[1], opts)
                    if name is None:
                        cfgs[c]['errors'] += [lc]
                    elif name not in cfgs:
                        raise error.general('include: %s: not present' %
                                            (ls[1]))
                    else:
                        cfgs[name]['refs'] += 1
            elif cfgs[c]['ext'] == '.bset' and ':' not in l:
                for ext in ['', '.cfg', '.bset']:
                    name = _find(l + ext, opts)
                    if name is not None:
                        if name not in cfgs:
                            raise error.general('include: %s: not present' %
                                                (ls[1]))
                        else:
                            cfgs[name]['refs'] += 1
                        break

    topdir = opts.defaults.expand('%{_topdir}')

    orphans = []
    show = True

    for c in cfgs:
        if cfgs[c]['refs'] == 0:
            orphans += [c]
        if len(cfgs[c]['errors']) != 0:
            if show:
                print('Warnings:')
                show = False
            print(' %s:' % (path.relpath(c)))
            for l in cfgs[c]['errors']:
                print('  %3d: %s' % (l, cfgs[c]['src'][l - 1][:-1]))

    show = True

    for o in sorted(orphans):
        if show:
            print('Orphans:')
            show = False
        print(' %s' % (path.relpath(o)))


def run():
    import sys
    try:
        _opts = options.load(args=sys.argv, logfile=False)
        log.notice('RTEMS Source Builder - Check, %s' % (version.string()))

        orphans = _opts.parse_args('--check-orphans', error=False, extra=False)
        if orphans:
            print('Checking for orphans...')
            check_orphans(_opts)
        else:
            if host_setup(_opts):
                print('Environment is ok')
            else:
                print('Environment is not correctly set up')
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


if __name__ == '__main__':
    run()
