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
# Check the defaults for a specific host.
#

import os

import defaults
import error
import execute
import log
import path

#
# Version of Sourcer Builder Check.
#
version = '0.1'

def _notice(opts, text):
    if not opts.quiet() and log.default and not log.default.has_stdout():
        print text
    log.output(text)
    log.flush()


def _check_none(_opts, macro, value, constraint):
    return True


def _check_triplet(_opts, macro, value, constraint):
    return True


def _check_dir(_opts, macro, value, constraint):
    if constraint != 'none' and not path.isdir(value):
        if constraint == 'required':
            _notice(_opts, 'error: dir: not found: (%s) %s' % (macro, value))
            return False
        if _opts.warn_all():
            _notice(_opts, 'warning: dir: not found: (%s) %s' % (macro, value))
    return True


def _check_exe(_opts, macro, value, constraint):

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
            _notice(_opts,
                    'warning: exe: absolute exe found in path: (%s) %s' % (macro, orig_value))
        return True

    if constraint == 'optional':
        if _opts.trace():
            _notice(_opts, 'warning: exe: optional exe not found: (%s) %s' % (macro, orig_value))
        return True

    _notice(_opts, 'error: exe: not found: (%s) %s' % (macro, orig_value))
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

def host_setup(_opts, _defaults):
    """ Basic sanity check. All executables and directories must exist."""

    checks = { 'none':    _check_none,
               'triplet': _check_triplet,
               'dir':     _check_dir,
               'exe':     _check_exe }

    sane = True

    for d in sorted(_defaults.iterkeys()):
        try:
            (test, constraint, value) = _defaults[d]
        except:
            raise error.general('invalid default: %s [%r]' % (d, _defaults[d]))
        if test != 'none':
            value = _opts.expand(value, _defaults)
            if test not in checks:
                raise error.general('invalid check test: %s [%r]' % (test, _defaults[d]))
            ok = checks[test](_opts, d, value, constraint)
            if _opts.trace():
                if ok:
                    tag = ' '
                else:
                    tag = '*'
                _notice(_opts, '%c %15s: %r -> "%s"' % (tag, d, _defaults[d], value))
            if sane and not ok:
                sane = False

    return sane


def run():
    import sys
    try:
        _opts, _defaults = defaults.load(args = sys.argv)
        if host_setup(_opts, _defaults):
            print 'Source Builder environent is ok'
        else:
            print 'Source Builder environent is not correctly set up'
    except error.general, gerr:
        print gerr
        sys.exit(1)
    except error.internal, ierr:
        print ierr
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    run()
