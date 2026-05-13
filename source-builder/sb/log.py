#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2017 Chris Johns (chrisj@rtems.org)
# All rights reserved.
#
# This file is part of the RTEMS Tools package in 'rtems-testing'.
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
# Log output to stdout and/or a file.
#

from __future__ import print_function

import os
import sys

from . import error

#
# A global log.
#
default = None

#
# A global capture handler.
#
capture = None

#
# Global parameters.
#
tracing = False
quiet = False


def set_default_once(log):
    global default
    if default is None:
        default = log


def _output(text=os.linesep, log=None):
    """Output the text to a log if provided else send it to stdout."""
    if text is None:
        text = os.linesep
    if type(text) is list:
        _text = ''
        for l in text:
            _text += l + os.linesep
        text = _text
    if log:
        log.output(text)
    elif default is not None:
        default.output(text)
    else:
        for l in text.replace(chr(13), '').splitlines():
            print(l)
        sys.stdout.flush()


def stdout_raw(text=os.linesep):
    print(text, end='')
    sys.stdout.flush()


def stderr(text=os.linesep, log=None):
    for l in text.replace(chr(13), '').splitlines():
        print(l, file=sys.stderr)
        sys.stderr.flush()
    if capture is not None:
        capture(text)


def output(text=os.linesep, log=None):
    if not quiet:
        _output(text, log)


def notice(text=os.linesep, log=None):
    if not quiet and default is not None and not default.has_stdout():
        for l in text.replace(chr(13), '').splitlines():
            print(l)
        sys.stdout.flush()
        if capture is not None:
            capture(text)
    _output(text, log)


def trace(text=os.linesep, log=None):
    if not quiet and tracing:
        _output(text, log)


def warning(text=os.linesep, log=None):
    for l in text.replace(chr(13), '').splitlines():
        notice('warning: %s' % (l), log)


def flush(log=None):
    if log:
        log.flush()
    elif default is not None:
        default.flush()


def tail(log=None):
    if log is not None:
        return log.tail
    if default is not None:
        return default.tail
    return 'No log output'


class log:
    """Log output to stdout or a file."""

    def __init__(self, streams=None, tail_size=400):
        self.tail = []
        self.tail_size = tail_size
        self.fhs = [None, None]
        if streams:
            for s in streams:
                if s == 'stdout':
                    self.fhs[0] = sys.stdout
                elif s == 'stderr':
                    self.fhs[1] = sys.stderr
                else:
                    try:
                        self.fhs.append(open(s, 'w'))
                    except IOError as ioe:
                        raise error.general("creating log file '" + s + \
                                            "': " + str(ioe))

    def __del__(self):
        for f in range(2, len(self.fhs)):
            self.fhs[f].close()

    def __str__(self):
        t = ''
        for tl in self.tail:
            t += tl + os.linesep
        return t[:-len(os.linesep)]

    def _tail(self, text):
        if type(text) is not list:
            text = text.splitlines()
        self.tail += text
        if len(self.tail) > self.tail_size:
            self.tail = self.tail[-self.tail_size:]

    def has_stdout(self):
        return self.fhs[0] is not None

    def has_stderr(self):
        return self.fhs[1] is not None

    def output(self, text):
        """Output the text message to all the logs."""
        # Reformat the text to have local line types.
        text = text.replace(chr(13), '').splitlines()
        self._tail(text)
        out = ''
        for l in text:
            out += l + os.linesep
        for f in range(0, len(self.fhs)):
            if self.fhs[f] is not None:
                self.fhs[f].write(out)
        self.flush()

    def flush(self):
        """Flush the output."""
        for f in range(0, len(self.fhs)):
            if self.fhs[f] is not None:
                self.fhs[f].flush()


if __name__ == "__main__":
    l = log(['stdout', 'log.txt'], tail_size=20)
    for i in range(0, 10):
        l.output('log: hello world: %d\n' % (i))
    l.output('log: hello world CRLF\r\n')
    l.output('log: hello world NONE')
    l.flush()
    print('=-' * 40)
    print('tail: %d' % (len(l.tail)))
    print(l)
    print('=-' * 40)
    for i in range(0, 10):
        l.output('log: hello world 2: %d\n' % (i))
    l.flush()
    print('=-' * 40)
    print('tail: %d' % (len(l.tail)))
    print(l)
    print('=-' * 40)
    for i in [0, 1]:
        quiet = False
        tracing = False
        print('- quiet:%s - trace:%s %s' %
              (str(quiet), str(tracing), '-' * 30))
        trace('trace with quiet and trace off')
        notice('notice with quiet and trace off')
        quiet = True
        tracing = False
        print('- quiet:%s - trace:%s %s' %
              (str(quiet), str(tracing), '-' * 30))
        trace('trace with quiet on and trace off')
        notice('notice with quiet on and trace off')
        quiet = False
        tracing = True
        print('- quiet:%s - trace:%s %s' %
              (str(quiet), str(tracing), '-' * 30))
        trace('trace with quiet off and trace on')
        notice('notice with quiet off and trace on')
        quiet = True
        tracing = True
        print('- quiet:%s - trace:%s %s' %
              (str(quiet), str(tracing), '-' * 30))
        trace('trace with quiet on and trace on')
        notice('notice with quiet on and trace on')
        default = l
    print('=-' * 40)
    print('tail: %d' % (len(l.tail)))
    print(l)
    print('=-' * 40)
    del l
