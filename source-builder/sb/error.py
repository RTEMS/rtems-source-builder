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

from __future__ import print_function

#
# Various errors we can raise.
#


class error(Exception):
    """Base class for Builder exceptions."""

    def set_output(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class general(error):
    """Raise for a general error."""

    def __init__(self, what):
        self.set_output('error: ' + str(what))


class internal(error):
    """Raise for an internal error."""

    def __init__(self, what):
        self.set_output('internal error: ' + str(what))


class exit(error):
    """Raise for to exit."""

    def __init__(self):
        pass


if __name__ == '__main__':
    try:
        raise general('a general error')
    except general as gerr:
        print('caught:', gerr)
    try:
        raise internal('an internal error')
    except internal as ierr:
        print('caught:', ierr)
