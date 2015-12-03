#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2015 Chris Johns (chrisj@rtems.org)
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
# To release the RSB create a git archive and then add a suitable VERSION file
# to the top directory.
#

import sys

import error
import git
import path

major = 4
minor = 11
revision = 0

#
# Default to an internal string.
#
_version_str =  '%d.%d.%d' % (major, minor, revision)
_released = False
_git = False

def _top():
    top = path.dirname(sys.argv[0])
    if len(top) == 0:
        top = '.'
    return top

def _load_released_version():
    global _released
    global _version_str
    top = _top()
    for ver in [top, '..']:
        if path.exists(path.join(ver, 'VERSION')):
            try:
                with open(path.join(ver, 'VERSION')) as v:
                    _version_str = v.readline().strip()
                v.close()
                _released = True
            except:
                raise error.general('Cannot access the VERSION file')
    return _released

def _load_git_version():
    global _git
    global _version_str
    repo = git.repo(_top())
    if repo.valid():
        head = repo.head()
        if repo.dirty():
            modified = ' modified'
        else:
            modified = ''
        _version_str = '%d.%d.%d (%s%s)' % (major, minor, revision, head[0:12], modified)
        _git = True
    return _git

def released():
    return _load_released_version()

def version_control():
    return _load_git_version()

def str():
    if not _released and not _git:
        if not _load_released_version():
            _load_git_version()
    return _version_str

if __name__ == '__main__':
    print 'major = %d' % (major)
    print 'minor = %d' % (minor)
    print 'revision = %d' % (revision)
    print 'Version: %s' % (str())
