#! /usr/bin/env python
#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2014-2016 Chris Johns (chrisj@rtems.org)
# All rights reserved.
#
# This file is part of the RTEMS Tools package in 'rtems-tools'.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

#
# Pkg-config in python. It attempts to provide a few simple features
# provided by the full pkg-config so packages can configure and build.
#

from __future__ import print_function

import copy
import os
import os.path
import re
import shlex
import sys

from . import path

def default_prefix(common = True):
    paths = []
    #
    # We have two paths to work around an issue in MSYS2 and the
    # conversion of Windows paths to shell paths.
    #
    if 'PKG_CONFIG_DEFAULT_PATH' in os.environ:
        for p in os.environ['PKG_CONFIG_DEFAULT_PATH'].split(os.pathsep):
            paths += [path.shell(p)]
    if 'PKG_CONFIG_PATH' in os.environ:
        for p in os.environ['PKG_CONFIG_PATH'].split(os.pathsep):
            paths += [path.shell(p)]
    if common:
        defaults = ['/usr',
                    '/usr/share',
                    '/lib',
                    '/lib64',
                    '/usr/lib',
                    '/usr/lib64',
                    '/usr/local']
        for d in defaults:
            for cp in package.config_prefixes:
                prefix = path.join(d, cp, 'pkgconfig')
                if path.exists(prefix):
                    paths += [prefix]
    return paths

class error(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

class package(object):

    node_types = ['requires', 'requires.private']
    node_type_labels = { 'requires': 'r',
                         'requires.private': 'rp',
                         'failed': 'F' }
    version_ops = ['=', '<', '>', '<=', '>=', '!=']
    config_prefixes = ['lib', 'libdata']
    get_recursion = ['cflags', 'libs']
    no_dup_flags = ['-I', '-l', '-L']
    dual_opts = ['-D', '-U', '-I', '-l', '-L']
    lib_list_splitter = re.compile(r'[\s,]+')
    loaded_prefixes = None
    loaded = {}

    @staticmethod
    def _copy(src, dst):
        dst.name_ = src.name_
        dst.file_ = src.file_
        dst.defines = copy.copy(src.defines)
        dst.fields = copy.copy(src.fields)
        dst.nodes = copy.copy(src.nodes)

    @staticmethod
    def _is_string(us):
        if type(us) == str:
            return True
        try:
            if type(us) == unicode:
                return True
        except:
            pass
        try:
            if type(us) == bytes:
                return True
        except:
            pass
        return False

    @staticmethod
    def is_version(v):
        for n in v.split('.'):
            if not n.isdigit():
                return False
        return True

    @staticmethod
    def splitter(pkg_list):
        pkgs = []
        if type(pkg_list) == list:
            pls = []
            for p in pkg_list:
                pls += package.lib_list_splitter.split(p)
        else:
            pls = package.lib_list_splitter.split(pkg_list)
        i = 0
        while i < len(pls):
            pkg = [pls[i]]
            i += 1
            if i < len(pls):
                op = None
                if package.is_version(pls[i]):
                    op = '>='
                    ver = pls[i]
                    i += 1
                elif pls[i] in package.version_ops:
                    op = pls[i]
                    i += 1
                    if i < len(pls):
                        ver = pls[i]
                        i += 1
                else:
                    op = '>='
                    ver = '0'
                pkg += [op, ver]
            else:
                pkg += ['>=', '0']
            pkgs += [pkg]
        return pkgs

    @staticmethod
    def check_versions(lhs, op, rhs):
        if op not in package.version_ops:
            raise error('bad operator: %s' % (op))
        if not lhs or not rhs:
            return False
        slhs = lhs.split('.')
        srhs = rhs.split('.')
        ok = True
        i = 0
        while i < len(srhs):
            try:
                l = int(slhs[i])
                r = int(srhs[i])
            except:
                return False
            if op == '=':
                if l != r:
                    ok = False
                    break
            elif op == '<':
                if l < r:
                    break
                if l >= r:
                    ok = False
                    break
            elif op == '>':
                if l > r:
                    break
                if l <= r:
                    ok = False
                    break
            elif op == '<=':
                if l < r:
                    break
                if l > r:
                    ok = False
                    break
            elif op == '>=':
                if l > r:
                    break
                if l < r:
                    ok = False
                    break
            elif op == '!=':
                if l != r:
                    ok = True
                    break
                if l == r:
                    ok = False
            i += 1
        return ok

    @staticmethod
    def dump_loaded():
        for n in sorted(package.loaded):
            print(package.loaded[n]._str())

    def __init__(self, name = None, prefix = None,
                 libs_scan = False, output = None, src = None):
        self._clean()
        self.name_ = name
        self.libs_scan = libs_scan
        self.output = output
        self.src = src
        self.prefix = None
        self.paths = []
        if prefix is None:
            prefix = default_prefix()
        if prefix:
            self._log('prefix: %s' % (prefix))
            if self._is_string(prefix):
                prefix = str(prefix)
                self.prefix = []
                for p in prefix.split(os.pathsep):
                    self.prefix += [path.shell(p)]
            elif type(prefix) is list:
                self.prefix = prefix
            else:
                raise error('invalid type of prefix: %s' % (type(prefix)))
            for p in self.prefix:
                if path.exists(p):
                    self.paths += [p]
            self._log('paths: %s' % (', '.join(self.paths)))
        if 'sysroot' in self.defines:
            self._log('sysroot: %s' % (self.defines['sysroot']))
        if 'top_builddir' in self.defines:
            self._log('top_builddir: %s' % (self.defines['top_builddir']))
        if self.name_:
            self.load(self.name_)

    def __str__(self):
        s = self._str()
        for nt in package.node_types:
            for n in sorted(self.nodes[nt]):
                s += ' ' + \
                     ' '.join(['%s%s' % (s, os.linesep) \
                               for s in str(self.nodes[nt][n]).split(os.linesep)])
        return s[:-1]

    def _str(self):
        if self.file_ or len(self.libraries):
            e = 'E'
        else:
            e = '-'
        s = '> %s %s (%s)%s' % (self.name_, e, self.file_, os.linesep)
        for d in sorted(self.defines):
            s += 'd: %s: %s%s' % (d, self.defines[d], os.linesep)
        for f in sorted(self.fields):
            s += 'f: %s: %s%s' % (f, self.fields[f], os.linesep)
        for l in sorted(self.libraries):
            s += 'l: %s%s' % (l, os.linesep)
        for nt in package.node_types + ['failed']:
            s += '%s: ' % (package.node_type_labels[nt])
            if len(self.nodes[nt]):
                txt = []
                for n in sorted(self.nodes[nt]):
                    if self.nodes[nt][n].exists():
                        e = ''
                    else:
                        e = '*'
                    txt += ['%s%s' % (n, e)]
                s += '%s%s' % (', '.join(txt), os.linesep)
            else:
                s += 'none' + os.linesep
        return s #[:-1]

    def _clean(self):
        self.name_ = None
        self.file_ = None
        self.defines = {}
        self.fields = {}
        self.nodes = { 'failed': {} }
        for nt in package.node_types:
            self.nodes[nt] = {}
        self.libraries = []
        if 'PKG_CONFIG_SYSROOT_DIR' in os.environ:
            self.defines['sysroot'] = os.environ['PKG_CONFIG_SYSROOT_DIR']
        if 'PKG_CONFIG_BUILD_TOP_DIR' in os.environ:
            self.defines['top_builddir'] = os.environ['PKG_CONFIG_BUILD_TOP_DIR']

    def _log(self, s):
        if self.output:
            self.output(s)

    def _find_package(self, name):
        if len(self.paths):
            for p in self.paths:
                pc = path.join(p, '%s.pc' % (name))
                if path.isfile(pc):
                    return pc;
        return None

    def _find_libraries(self, name):
        libraries = []
        if self.libs_scan:
            for prefix in self.prefix:
                prefix = path.join(prefix, 'lib')
                if path.exists(prefix):
                    for l in os.listdir(path.host(prefix)):
                        if l.startswith(name + '.'):
                            libraries += [path.join(prefix, l)]
                            break
        return libraries

    def _filter_sysroot(self, s):
        if 'sysroot' in self.defines:
            sysroot = self.defines['sysroot']
            offset = 0
            while True:
                dash = s[offset:].find('-')
                if dash < 0:
                    break
                if offset + dash + 2 < len(s) and s[offset + dash + 1] in 'LI':
                    s = s[:offset + dash + 2] + sysroot + s[offset + dash + 2:]
                offset += dash + 1
        return s

    def _filter_top_builddir(self, s):
        if 'top_builddir' in self.defines:
            top_builddir = self.defines['top_builddir']
            if self.file_.startswith(top_builddir):
                offset = 0
                while True:
                    dash = s[offset:].find('-')
                    if dash < 0:
                        break
                    if offset + dash + 2 < len(s) and s[offset + dash + 1] in 'LI':
                        p = s[offset + dash + 2:]
                        if not p.startswith(top_builddir):
                            s = s[:offset + dash + 2] + top_builddir + p
                    offset += dash + 1
        return s

    def _filter_duplicates(self, s):
        clean = ''
        present = {}
        ss = shlex.split(s)
        i = 0
        while i < len(ss):
            added = False
            for do in package.dual_opts:
                if ss[i].startswith(do):
                    if ss[i] == do:
                        i += 1
                        if i == len(ss):
                            clean += ' %s' % (do)
                        else:
                            key = '%s%s' % (do, ss[i])
                            if key not in present:
                                if ' ' in ss[i]:
                                    clean += ' %s"%s"' % (do, ss[i])
                                else:
                                    clean += ' %s' % (key)
                    else:
                        key = ss[i]
                        if key not in present:
                            clean += ' %s' % (key)
                    added = True
                    present[key] = True
                    break
            if not added:
                if ss[i] not in present:
                    clean += ' %s' % (ss[i])
                    present[ss[i]] = True
            i += 1
        return clean

    def _filter(self, s):
        s = self._filter_top_builddir(s)
        s = self._filter_sysroot(s)
        s = self._filter_duplicates(s)
        return s.strip()

    def _splitter(self, pkg_list):
        pkgs = []
        pls = pkg_list.split()
        i = 0
        while i < len(pls):
            pkg = [pls[i]]
            i += 1
            if i < len(pls) and pls[i] in package.version_ops:
                pkg += [pls[i]]
                i += 1
                if i < len(ls):
                    pkg += [pls[i]]
                    i += 1
            pkgs += [pkg]
        return pkgs

    def name_from_file(self, file = None):
        if file is None:
            file = self.file_
        if file is None:
            return None
        name = path.basename(file)
        if name.endswith('.pc'):
            name = name[:-3]
        return name

    def name(self):
        return self.name_

    def file(self):
        return self.file_

    def exists(self):
        ok = False
        if self.file_:
            ok = True
        if self.libraries:
            ok = True
        return ok

    def load(self, name):
        self._log('loading: %s' % (name))
        if self.name_:
            self._clean()
        self.name_ = name
        file = self._find_package(name)
        if file:
            if file in package.loaded:
                package._copy(package.loaded[file], self)
                return
            self._log('load: %s (%s)' % (name, file))
            if self.src:
                self.src('==%s%s' % ('=' * 80, os.linesep))
                self.src(' %s %s%s' % (file, '=' * (80 - len(file)), os.linesep))
                self.src('==%s%s' % ('=' * 80, os.linesep))
            f = open(path.host(file))
            tm = False
            for l in f.readlines():
                if self.src:
                    self.src(l)
                l = l[:-1]
                hash = l.find('#')
                if hash >= 0:
                    l = l[:hash]
                if len(l):
                    d = 0
                    define = False
                    eq = l.find('=')
                    dd = l.find(':')
                    if eq > 0 and dd > 0:
                        if eq < dd:
                            define = True
                            d = eq
                        else:
                            define = False
                            d = dd
                    elif eq >= 0:
                        define = True
                        d = eq
                    elif dd >= 0:
                        define = False
                        d = dd
                    if d > 0:
                        lhs = l[:d].lower()
                        rhs = l[d + 1:]
                        if tm:
                            print(('define: ' + str(define) + ', lhs: ' + lhs + ', ' + rhs))
                        if define:
                            self.defines[lhs] = rhs
                        else:
                            self.fields[lhs] = rhs
            self.file_ = file
        else:
            self.libraries = self._find_libraries(name)
        for nt in package.node_types:
            requires = self.get(nt, private = False)
            if requires:
                for r in package.splitter(requires):
                    if r[0] not in self.nodes[nt]:
                        file = self._find_package(r[0])
                        if file in package.loaded:
                            pkg = package.loaded[file]
                        else:
                            pkg = package(r[0], self.prefix, self.output)
                        ver = pkg.get('version')
                        self._log(' checking: %s (%s) %s %s' % (r[0], ver, r[1], r[2]))
                        if ver and package.check_versions(ver, r[1], r[2]):
                            self.nodes[nt][r[0]] = pkg
                        else:
                            self._log('failed: %s (%s %s %s)' % (r[0], ver, r[1], r[2]))
                            self.nodes['failed'][r[0]] = pkg
        if self.exists():
            self._log('load: exists and loaded; cache as loaded')
            package.loaded[self.file_] = self

    def get(self, label, private = True):
        self._log('get: %s (%s)' % (label, ','.join(self.fields)))
        if label.lower() not in self.fields:
            return None
        s = ''
        if self.file_:
            mre = re.compile(r'\$\{[^\}]+\}')
            s = self.fields[label.lower()]
            expanded = True
            tm = False
            while expanded:
                expanded = False
                if tm:
                    self._log('pc:get: "' + s + '"')
                ms = mre.findall(s)
                for m in ms:
                    mn = m[2:-1]
                    if mn.lower() in self.defines:
                        s = s.replace(m, self.defines[mn.lower()])
                        expanded = True
            if label in package.get_recursion:
                for nt in package.node_types:
                    if 'private' not in nt or ('private' in nt and private):
                        for n in self.nodes[nt]:
                            r = self.nodes[nt][n].get(label, private = private)
                            self._log('node: %s: %s' % (self.nodes[nt][n].name(), r))
                            if r:
                                s += ' ' + r
        elif label == 'libs' and len(self.libraries):
            s = '-l%s' % (self.name_[3:])
        return self._filter(s)

    def check(self, op, version):
        self._log('checking: %s %s %s' % (self.name_, op, version))
        ok = False
        if self.file_:
            pkgver = self.get('version')
            if pkgver is None:
                self._log('check: %s %s failed (no version)' % (op, version))
                return False
            ok = package.check_versions(pkgver, op, version)
            if ok:
                self._log('check: %s %s %s ok' % (pkgver, op, version))
            else:
                self._log('check: %s %s %s failed' % (pkgver, op, version))
        else:
            if len(self.libraries):
                ok = True
            else:
                self._log('check: %s not found' % (self.name_))
        return ok

def check_package(libraries, args, output, src):
    ec = 1
    pkg = None
    flags = { 'cflags': '',
              'libs': '' }
    output('libraries: %s' % (libraries))
    libs = package.splitter(libraries)
    for lib in libs:
        output('pkg: %s' % (lib))
        pkg = package(lib[0], prefix = args.prefix, output = output, src = src)
        if args.dump:
            output(pkg)
        if pkg.exists():
            if len(lib) == 1:
                if args.exact_version:
                    if pkg.check('=', args.exact_version):
                        ec = 0
                elif args.atleast_version:
                    if pkg.check('>=', args.atleast_version):
                        ec = 0
                elif args.max_version:
                    if pkg.check('<=', args.max_version):
                        ec = 0
                else:
                    ec = 0
            else:
                if len(lib) != 3:
                    raise error('invalid package check: %s' % (' '.join(lib)))
                if pkg.check(lib[1], lib[2]):
                    ec = 0
            if ec == 0:
                cflags = pkg.get('cflags')
                if cflags:
                    flags['cflags'] += cflags
                libs = pkg.get('libs', private = False)
                if libs:
                    flags['libs'] += libs
                break
        if ec > 0:
            break
    return ec, pkg, flags
