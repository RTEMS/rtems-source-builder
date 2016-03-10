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
# To release the RSB create a git archive and then add a suitable VERSION file
# to the top directory.
#

from __future__ import print_function

import sys

import error
import git
import path
import sources

#
# Default to an internal string.
#
_version = '4.12'
_revision = 'not_released'
_version_str = '%s.%s' % (_version, _revision)
_released = False
_git = False

def _top():
    top = path.dirname(sys.argv[0])
    if len(top) == 0:
        top = '.'
    return top

def _load_released_version_config():
    top = _top()
    for ver in [top, '..']:
        if path.exists(path.join(ver, 'VERSION')):
            try:
                import configparser
            except ImportError:
                import ConfigParser as configparser
            v = configparser.SafeConfigParser()
            v.read(path.join(ver, 'VERSION'))
            return v
    return None

def _load_released_version():
    global _released
    global _version_str
    v = _load_released_version_config()
    if v is not None:
        _version_str = v.get('version', 'release')
        _released = True
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
        _version_str = '%s (%s%s)' % (_version, head[0:12], modified)
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

def load_release_hashes(macros):
    def hash_error(msg):
        raise error.general(msg)

    if released():
        v = _load_released_version_config()
        if v is not None:
            try:
                hashes = v.items('hashes')
            except:
                hashes = []
            for hash in hashes:
                hs = hash[1].split()
                if len(hs) != 2:
                    raise error.general('invalid release hash in VERSION')
                sources.hash((hs[0], hash[0], hs[1]), macros, hash_error)

if __name__ == '__main__':
    print('Version: %s' % (str()))
