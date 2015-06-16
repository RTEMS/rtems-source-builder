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
# Manage paths locally. The internally the path is in Unix or shell format and
# we convert to the native format when performing operations at the Python
# level. This allows macro expansion to work.
#

import log
import os
import shutil
import stat
import string

import error

windows = os.name == 'nt'

def host(path):
    if path is not None:
        while '//' in path:
            path = path.replace('//', '/')
        if windows:
            if len(path) > 2 and \
               path[0] == '/' and path[2] == '/' and \
               (path[1] in string.ascii_lowercase or \
                path[1] in string.ascii_uppercase):
                path = '%s:%s' % (path[1], path[2:])
            path = path.replace('/', '\\')
            if not path.startswith('\\\\?\\') and len(path) > 254:
                path = '\\\\?\\' + path
    return path

def shell(path):
    if path is not None:
        if windows:
            if path.startswith('\\\\?\\'):
                path = path[4:]
            if len(path) > 1 and path[1] == ':':
                path = '/%s%s' % (path[0], path[2:])
            path = path.replace('\\', '/')
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
    #
    # Perform the removal of the directory tree manually so we can
    # make sure on Windows the files and correctly encoded to avoid
    # the size limit.
    #
    path = host(path)
    for root, dirs, files in os.walk(path, topdown = False):
        for name in files:
            file = host(os.path.join(root, name))
            if not os.path.islink(file) and not os.access(file, os.W_OK):
                os.chmod(file, stat.S_IWUSR)
            os.unlink(file)
        for name in dirs:
            dir = host(os.path.join(root, name))
            if os.path.islink(dir):
                os.unlink(dir)
            else:
                if not os.access(dir, os.W_OK):
                    os.chmod(dir, stat.S_IWUSR)
                os.rmdir(dir)
    if not os.path.islink(path) and not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
    if os.path.islink(path):
        os.unlink(path)
    else:
        os.rmdir(path)

def expand(name, paths):
    l = []
    for p in paths:
        l += [join(p, name)]
    return l

def copy(src, dst):
    hsrc = host(src)
    hdst = host(dst)
    try:
        shutil.copy(hsrc, hdst)
    except OSError, why:
        if windows:
            if WindowsError is not None and isinstance(why, WindowsError):
                pass
        else:
            raise error.general('copying tree: %s -> %s: %s' % (hsrc, hdst, str(why)))

def copy_tree(src, dst):
    trace = False

    hsrc = host(src)
    hdst = host(dst)

    if os.path.exists(hsrc):
        names = os.listdir(hsrc)
    else:
        names = []

    if trace:
        print 'path.copy_tree:'
        print '   src: %s' % (src)
        print '  hsrc: %s' % (hsrc)
        print '   dst: %s' % (dst)
        print '  hdst: %s' % (hdst)
        print ' names: %r' % (names)

    if not os.path.isdir(hdst):
        if trace:
            print ' mkdir: %s' % (hdst)
        os.makedirs(hdst)

    for name in names:
        srcname = host(os.path.join(hsrc, name))
        dstname = host(os.path.join(hdst, name))
        try:
            if os.path.islink(srcname):
                linkto = os.readlink(srcname)
                if os.path.exists(dstname):
                    if os.path.islink(dstname):
                        dstlinkto = os.readlink(dstname)
                        if linkto != dstlinkto:
                            log.warning('copying tree: link does not match: %s -> %s' % \
                                            (dstname, dstlinkto))
                            os.remove(dstname)
                    else:
                        log.warning('copying tree: destination is not a link: %s' % \
                                        (dstname))
                        os.remove(dstname)
                else:
                    os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copy_tree(srcname, dstname)
            else:
                    shutil.copy2(host(srcname), host(dstname))
        except shutil.Error, err:
            raise error.general('copying tree: %s -> %s: %s' % \
                                (hsrc, hdst, str(err)))
        except EnvironmentError, why:
            raise error.general('copying tree: %s -> %s: %s' % \
                                (srcname, dstname, str(why)))
    try:
        shutil.copystat(hsrc, hdst)
    except OSError, why:
        if windows:
            if WindowsError is not None and isinstance(why, WindowsError):
                pass
        else:
            raise error.general('copying tree: %s -> %s: %s' % (hsrc, hdst, str(why)))

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
    print join('s:/d/e\\f/g', '/h', '/tyty/zxzx', '\\mm\\nn/p')
