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
# Manage paths locally. The internally the path is in Unix or shell format and
# we convert to the native format when performing operations at the Python
# level. This allows macro expansion to work.
#

import os
import shutil
import string

import error

windows = os.name == 'nt'

def host(path):
    if path is not None:
        while '//' in path:
            path = path.replace('//', '/')
        if windows and len(path) > 2:
            if path[0] == '/' and path[2] == '/' and \
                    (path[1] in string.ascii_lowercase or \
                         path[1] in string.ascii_uppercase):
                path = ('%s:%s' % (path[1], path[2:])).replace('/', '\\')
    return path

def shell(path):
    if path is not None:
        if windows and len(path) > 1 and path[1] == ':':
            path = ('/%s%s' % (path[0], path[2:])).replace('\\', '/')
        while '//' in path:
            path = path.replace('//', '/')
    return path

def basename(path):
    return shell(os.path.basename(path))

def dirname(path):
    return shell(os.path.dirname(path))

def join(path, *args):
    path = shell(path)
    for arg in args:
        if len(path):
            path += '/' + shell(arg)
        else:
            path = shell(arg)
    return shell(path)

def abspath(path):
    return shell(os.path.abspath(host(path)))

def splitext(path):
    root, ext = os.path.splitext(host(path))
    return shell(root), ext

def exists(paths):
    if type(paths) == list:
        results = []
        for p in paths:
            results += [os.path.exists(host(p))]
        return results
    return os.path.exists(host(paths))

def isdir(path):
    return os.path.isdir(host(path))

def isfile(path):
    return os.path.isfile(host(path))

def isabspath(path):
    return path[0] == '/'

def iswritable(path):
    return os.access(host(path), os.W_OK)

def ispathwritable(path):
    path = host(path)
    while len(path) != 0:
        if os.path.exists(path):
            return iswritable(path)
        path = os.path.dirname(path)
    return False

def mkdir(path):
    path = host(path)
    if exists(path):
        if not isdir(path):
            raise error.general('path exists and is not a directory: %s' % (path))
    else:
        if windows:
            try:
                os.makedirs(host(path))
            except IOError, err:
                raise error.general('cannot make directory: %s' % (path))
            except OSError, err:
                raise error.general('cannot make directory: %s' % (path))
            except WindowsError, err:
                raise error.general('cannot make directory: %s' % (path))
        else:
            try:
                os.makedirs(host(path))
            except IOError, err:
                raise error.general('cannot make directory: %s' % (path))
            except OSError, err:
                raise error.general('cannot make directory: %s' % (path))

def removeall(path):

    def _onerror(function, path, excinfo):
        print 'removeall error: (%r) %s' % (function, path)

    path = host(path)
    shutil.rmtree(path, onerror = _onerror)
    return

def expand(name, paths):
    l = []
    for p in paths:
        l += [join(p, name)]
    return l

if __name__ == '__main__':
    print host('/a/b/c/d-e-f')
    print host('//a/b//c/d-e-f')
    print shell('/w/x/y/z')
    print basename('/as/sd/df/fg/me.txt')
    print dirname('/as/sd/df/fg/me.txt')
    print join('/d', 'g', '/tyty/fgfg')
    windows = True
    print host('/a/b/c/d-e-f')
    print host('//a/b//c/d-e-f')
    print shell('/w/x/y/z')
    print shell('w:/x/y/z')
    print basename('x:/sd/df/fg/me.txt')
    print dirname('x:/sd/df/fg/me.txt')
    print join('s:/d/', '/g', '/tyty/fgfg')
