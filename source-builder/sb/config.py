#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2018 Chris Johns (chrisj@rtems.org)
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
# This code is based on a tool I wrote to parse RPM spec files in the RTEMS
# project. This is now a configuration file format that has moved away from the
# spec file format to support the specific needs of cross-compiling GCC. This
# module parses a configuration file into Python data types that can be used by
# other software modules.
#

from __future__ import print_function

import copy
from functools import reduce
import os
import re
import sys

try:
    from . import error
    from . import execute
    from . import log
    from . import options
    from . import path
    from . import pkgconfig
    from . import sources
except KeyboardInterrupt:
    print('user terminated', file = sys.stderr)
    sys.exit(1)
except:
    raise

def _check_bool(value):
    istrue = None
    if value.isdigit():
        if int(value) == 0:
            istrue = False
        else:
            istrue = True
    else:
        if type(value) is str and len(value) == 2 and value[0] == '!':
            istrue = _check_bool(value[1])
            if type(istrue) is bool:
                istrue = not istrue
    return istrue

def _check_nil(value):
    if len(value):
        istrue = True
    else:
        istrue = False
    return istrue

class package:

    def __init__(self, name, arch, config):
        self._name = name
        self._arch = arch
        self.config = config
        self.directives = {}
        self.infos = {}
        self.sizes = {}

    def __str__(self):

        def _dictlist(dl):
            s = ''
            dll = list(dl.keys())
            dll.sort()
            for d in dll:
                if d:
                    s += '  ' + d + ':\n'
                    for l in dl[d]:
                        s += '    ' + l + '\n'
            return s

        s = '\npackage: ' + self._name + \
            '\n directives:\n' + _dictlist(self.directives) + \
            '\n infos:\n' + _dictlist(self.infos)

        return s

    def _macro_override(self, info, macro):
        '''See if a macro overrides this setting.'''
        overridden = self.config.macros.overridden(macro)
        if overridden:
            return self.config.macros.expand(macro)
        return info

    def directive_extend(self, dir, data):
        if dir not in self.directives:
            self.directives[dir] = []
        for i in range(0, len(data)):
            data[i] = data[i].strip()
        self.directives[dir].extend(data)
        self.config.macros[dir] = '\n'.join(self.directives[dir])

    def info_append(self, info, data):
        if info not in self.infos:
            self.infos[info] = []
        self.infos[info].append(data)
        self.config.macros[info] = '\n'.join(self.infos[info])

    def get_info(self, info, expand = True):
        if info in self.config.macros:
            _info = self.config.macros[info].split('\n')
            if expand:
                return self.config.expand(_info)
            else:
                return _info
        return None

    def extract_info(self, label, expand = True):
        ll = label.lower()
        infos = {}
        keys = self.config.macros.find('%s.*' % (ll))
        for k in keys:
            if k == ll:
                k = '%s0' % (ll)
            elif not k[len(ll):].isdigit():
                continue
            infos[k] = [self.config.expand(self.config.macros[k])]
        return infos

    def _find_macro(self, label, expand = True):
        if label in self.config.macros:
            macro = self.config.macros[label].split('\n')
            if expand:
                return self.config.expand(macro)
            else:
                return macro
        return None

    def find_info(self, label, expand = True):
        return self._find_macro(label, expand)

    def find_directive(self, label, expand = True):
        return self._find_macro(label, expand)

    def name(self):
        info = self.find_info('name')
        if info:
            n = info[0]
        else:
            n = self._name
        return self._macro_override(n, 'name')

    def summary(self):
        info = self.find_info('summary')
        if info:
            return info[0]
        return ''

    def url(self):
        info = self.find_info('url')
        if info:
            return info[0]
        return ''

    def version(self):
        info = self.find_info('version')
        if not info:
            return None
        return info[0]

    def release(self):
        info = self.find_info('release')
        if not info:
            return None
        return info[0]

    def buildarch(self):
        info = self.find_info('buildarch')
        if not info:
            return self._arch
        return info[0]

    def sources(self):
        return self.extract_info('source')

    def patches(self):
        return self.extract_info('patch')

    def prep(self):
        return self.find_directive('%prep')

    def build(self):
        return self.find_directive('%build')

    def install(self):
        return self.find_directive('%install')

    def clean(self):
        return self.find_directive('%clean')

    def include(self):
        return self.find_directive('%include')

    def testing(self):
        return self.find_directive('%testing')

    def long_name(self):
        return self.name()

    def disabled(self):
        return len(self.name()) == 0

    def set_size(self, what, path_):
        if what not in self.sizes:
            self.sizes[what] = 0
        self.sizes[what] += path.get_size(path_)

    def get_size(self, what):
        if what in self.sizes:
            return self.sizes[what]
        return 0

class file:
    """Parse a config file."""

    _directive = [ '%include',
                   '%description',
                   '%prep',
                   '%build',
                   '%clean',
                   '%install',
                   '%testing' ]

    _ignore = [ re.compile('%setup'),
                re.compile('%configure'),
                re.compile('%source'),
                re.compile('%patch'),
                re.compile('%hash'),
                re.compile('%select'),
                re.compile('%disable') ]

    def __init__(self, name, opts, macros = None):
        log.trace('config: %s: initialising' % (name))
        self.opts = opts
        self.init_name = name
        self.wss = re.compile(r'\s+')
        self.tags = re.compile(r':+')
        self.sf = re.compile(r'%\([^\)]+\)')
        self.set_macros(macros)
        self._reset(name)
        self.load(name)

    def __str__(self):

        def _dict(dd):
            s = ''
            ddl = list(dd.keys())
            ddl.sort()
            for d in ddl:
                s += '  ' + d + ': ' + dd[d] + '\n'
            return s

        s = 'config: %s' % ('.'.join(self.configpath)) + \
            '\n' + str(self.opts) + \
            '\nlines parsed: %d' % (self.lc) + \
            '\nname: ' + self.name + \
            '\nmacros:\n' + str(self.macros)
        for _package in self._packages:
            s += str(self._packages[_package])
        return s

    def _reset(self, name):
        self.parent = 'root'
        self.name = name
        self.load_depth = 0
        self.configpath = []
        self._includes = []
        self._packages = {}
        self.in_error = False
        self.lc = 0
        self.if_depth = 0
        self.conditionals = {}
        self._packages = {}
        self.package = 'main'
        self.disable_macro_reassign = False
        self.pkgconfig_prefix = None
        self.pkgconfig_crosscompile = False
        self.pkgconfig_filter_flags = False
        for arg in self.opts.args:
            if arg.startswith('--with-') or arg.startswith('--without-'):
                if '=' in arg:
                    label, value = arg.split('=', 1)
                else:
                    label = arg
                    value = None
                label = label[2:].lower().replace('-', '_')
                if value:
                    self.macros.define(label, value)
                else:
                    self.macros.define(label)

    def _relative_path(self, p):
        sbdir = None
        if '_sbdir' in self.macros:
            sbdir = path.dirname(self.expand('%{_sbdir}'))
            if p.startswith(sbdir):
                p = p[len(sbdir) + 1:]
        return p

    def _name_line_msg(self,  msg):
        return '%s:%d: %s' % (path.basename(self.name), self.lc,  msg)

    def _output(self, text):
        if not self.opts.quiet():
            log.output(text)

    def _error(self, msg):
        if not self.opts.dry_run():
            if self.opts.keep_going():
                err = 'error: %s' % (self._name_line_msg(msg))
                log.stderr(err)
                log.output(err)
                self.in_error = True
                log.stderr('warning: switched to dry run due to errors')
                self.opts.set_dry_run()
        raise error.general(self._name_line_msg(msg))

    def _label(self, name):
        if name.startswith('%{') and name[-1] == '}':
            return name
        return '%{' + name.lower() + '}'

    def _cross_compile(self):
        _host = self.expand('%{_host}')
        _build = self.expand('%{_build}')
        return _host != _build

    def _candian_cross_compile(self):
        _host = self.expand('%{_host}')
        _build = self.expand('%{_build}')
        _target = self.expand('%{_target}')
        _alloc_cxc = self.defined('%{allow_cxc}')
        return _alloc_cxc and _host != _build and _host != _target

    def _macro_split(self, s):
        '''Split the string (s) up by macros. Only split on the
           outter level. Nested levels will need to split with futher calls.'''
        trace_me = False
        if trace_me:
            print('------------------------------------------------------')
        macros = []
        nesting = []
        has_braces = False
        c = 0
        while c < len(s):
            if trace_me:
                print('ms:', c, '"' + s[c:] + '"', has_braces, len(nesting), nesting)
            #
            # We need to watch for shell type variables or the form '${var}' because
            # they can upset the brace matching.
            #
            if s[c] == '%' or s[c] == '$':
                start = s[c]
                c += 1
                if c == len(s):
                    continue
                #
                # Do we have '%%' or '%(' or '$%' or '$(' or not '${' ?
                #
                if s[c] == '%' or s[c] == '(' or (start == '$' and s[c] != '{'):
                    continue
                elif not s[c].isspace():
                    #
                    # If this is a shell macro and we are at the outter
                    # level or is '$var' forget it and move on.
                    #
                    if start == '$' and (s[c] != '{' or len(nesting) == 0):
                        continue
                    if s[c] == '{':
                        this_has_braces = True
                    else:
                        this_has_braces = False
                    nesting.append((c - 1, has_braces))
                    has_braces = this_has_braces
            elif len(nesting) > 0:
                if s[c] == '}' or (s[c].isspace() and not has_braces):
                    #
                    # Can have '%{?test: something %more}' where the
                    # nested %more ends with the '}' which also ends
                    # the outter macro.
                    #
                    if not has_braces:
                        if s[c] == '}':
                            macro_start, has_braces = nesting[len(nesting) - 1]
                            nesting = nesting[:-1]
                            if len(nesting) == 0:
                                macros.append(s[macro_start:c].strip())
                    if len(nesting) > 0:
                        macro_start, has_braces = nesting[len(nesting) - 1]
                        nesting = nesting[:-1]
                        if len(nesting) == 0:
                            macros.append(s[macro_start:c + 1].strip())
            c += 1
        if trace_me:
            print('ms:', macros)
        if trace_me:
            print('-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=')
        return macros

    def _shell(self, line, nesting = 0):
        #
        # Parse the line and handle nesting '()' pairs. If on Windows
        # handle embedded '"' (double quotes) as the command is run as
        # a double quoted string.
        #
        def _exec(shell_macro):
            output = ''
            if len(shell_macro) > 3:
                e = execute.capture_execution()
                if options.host_windows:
                    shell_cmd = \
                        ''.join([c if c != '"' else '\\' + c for c in shell_macro[2:-1]])
                    cmd = '%s -c "%s"' % (self.macros.expand('%{__sh}'), shell_cmd)
                else:
                    cmd = shell_macro[2:-1]
                exit_code, proc, output = e.shell(cmd)
                log.trace('shell-output: %d %s' % (exit_code, output))
                if exit_code != 0:
                    raise error.general('shell macro failed: %s: %d: %s' % (cmd,
                                                                            exit_code,
                                                                            output))
            return output

        if nesting > 200:
            raise error.general('shell macro failed: too many nesting levels')

        updating = True
        while updating:
            updating = False
            pos = line.find('%(')
            if pos >= 0:
                braces = 0
                for p in range(pos + 2, len(line)):
                    if line[p] == '(':
                        braces += 1
                    elif line[p] == ')':
                        if braces > 0:
                            braces -= 1
                        else:
                            shell_cmd = '%(' + \
                                self._shell(line[pos + 2:p], nesting + 1) + ')'
                            line = line[:pos] + _exec(shell_cmd) + line[p + 1:]
                            updating = True
                            break

        return line

    def _pkgconfig_check(self, test):
        # Hack to by pass pkgconfig checks when just wanting to download the
        # source.
        if self.macros['_dry_run'] == '1' and \
           ('with_download' in self.macros and self.macros['with_download'] == '1'):
            return '0'
        ok = False
        log.trace('pkgconfig: check: crossc=%d pkg_crossc=%d prefix=%s'
                  % ( self._cross_compile(),
                      self.pkgconfig_crosscompile,
                      self.pkgconfig_prefix))
        log.trace('pkgconfig: check: test=%s' % (test))
        if type(test) == str:
            test = test.split()
        if not self._cross_compile() or self.pkgconfig_crosscompile:
            try:
                pkg = pkgconfig.package(test[0],
                                        prefix = self.pkgconfig_prefix,
                                        output = self._output,
                                        src = log.trace)
                if len(test) != 1 and len(test) != 3:
                    self._error('malformed check: %s' % (' '.join(test)))
                else:
                    op = '>='
                    ver = '0'
                    if len(test) == 3:
                        op = test[1]
                        ver = self.macros.expand(test[2])
                    ok = pkg.check(op, ver)
            except pkgconfig.error as pe:
                self._error('pkgconfig: check: %s' % (pe))
            except:
                raise
                raise error.internal('pkgconfig failure')
        if ok:
            return '1'
        return '0'

    def _pkgconfig_flags(self, package, flags):
        pkg_flags = None
        if not self._cross_compile() or self.pkgconfig_crosscompile:
            try:
                pkg = pkgconfig.package(package,
                                        prefix = self.pkgconfig_prefix,
                                        output = self._output,
                                        src = log.trace)
                pkg_flags = pkg.get(flags)
                if pkg_flags and self.pkgconfig_filter_flags:
                    fflags = []
                    for f in pkg_flags.split():
                        if not f.startswith('-W'):
                            fflags += [f]
                    pkg_flags = ' '.join(fflags)
                log.trace('pkgconfig: %s:  %s' % (flags, pkg_flags))
            except pkgconfig.error as pe:
                self._error('pkgconfig: %s:  %s' % (flags, pe))
            except:
                raise
                raise error.internal('pkgconfig failure')
        if pkg_flags is None:
            pkg_flags = ''
        return pkg_flags

    def _pkgconfig(self, pcl):
        ok = False
        ps = ''
        if pcl[0] == 'check':
            ps = self._pkgconfig_check(pcl[1:])
        elif pcl[0] == 'prefix':
            if len(pcl) == 2:
                self.pkgconfig_prefix = pcl[1]
            else:
                self._error('prefix error: %s' % (' '.join(pcl)))
        elif pcl[0] == 'crosscompile':
            ok = True
            if len(pcl) == 2:
                if pcl[1].lower() == 'yes':
                    self.pkgconfig_crosscompile = True
                elif pcl[1].lower() == 'no':
                    self.pkgconfig_crosscompile = False
                else:
                    ok = False
            else:
                ok = False
            if not ok:
                self._error('crosscompile error: %s' % (' '.join(pcl)))
        elif pcl[0] == 'filter-flags':
            ok = True
            if len(pcl) == 2:
                if pcl[1].lower() == 'yes':
                    self.pkgconfig_filter_flags = True
                elif pcl[1].lower() == 'no':
                    self.pkgconfig_filter_flags = False
                else:
                    ok = False
            else:
                ok = False
            if not ok:
                self._error('crosscompile error: %s' % (' '.join(pcl)))
        elif pcl[0] in ['ccflags', 'cflags', 'ldflags', 'libs']:
            ps = self._pkgconfig_flags(pcl[1], pcl[0])
        else:
            self._error('pkgconfig error: %s' % (' '.join(pcl)))
        return ps

    def _expand(self, s):
        expand_count = 0
        expanded = True
        while expanded:
            expand_count += 1
            if expand_count > 500:
                raise error.general('macro expand looping: %s' % (s))
            expanded = False
            ms = self._macro_split(s)
            for m in ms:
                mn = m
                #
                # A macro can be '%{macro}' or '%macro'. Turn the later into
                # the former.
                #
                show_warning = True
                if mn[1] != '{':
                    for r in self._ignore:
                        if r.match(mn) is not None:
                            mn = None
                            break
                    else:
                        mn = self._label(mn[1:])
                        show_warning = False
                elif m.startswith('%{expand'):
                    colon = m.find(':')
                    if colon < 8:
                        log.warning(self._name_line_msg('malformed expand macro, ' \
                                                        'no colon found'))
                    else:
                        e = self._expand(m[colon + 1:-1].strip())
                        s = s.replace(m, self._label(e))
                        expanded = True
                        mn = None
                elif m.startswith('%{with '):
                    #
                    # Change the ' ' to '_' because the macros have no spaces.
                    #
                    n = self._label('with_' + m[7:-1].strip())
                    if n in self.macros:
                        s = s.replace(m, '1')
                    else:
                        s = s.replace(m, '0')
                    expanded = True
                    mn = None
                elif m.startswith('%{echo'):
                    if not m.endswith('}'):
                        log.warning(self._name_line_msg("malformed conditional macro '%s'" % (m)))
                        mn = None
                    else:
                        e = self._expand(m[6:-1].strip())
                        log.notice('%s' % (self._name_line_msg(e)))
                        s = ''
                        expanded = True
                        mn = None
                elif m.startswith('%{defined'):
                    n = self._label(m[9:-1].strip())
                    if n in self.macros:
                        s = s.replace(m, '1')
                    else:
                        s = s.replace(m, '0')
                    expanded = True
                    mn = None
                elif m.startswith('%{!defined'):
                    n = self._label(m[10:-1].strip())
                    if n in self.macros:
                        s = s.replace(m, '0')
                    else:
                        s = s.replace(m, '1')
                    expanded = True
                    mn = None
                elif m.startswith('%{triplet'):
                    triplet = m[len('%{triplet'):-1].strip().split()
                    ok = False
                    if len(triplet) == 2:
                        macro = self._expand(triplet[0])
                        value = self._expand(triplet[1])
                        vorig = value
                        arch_value = ''
                        vendor_value = ''
                        os_value = ''
                        dash = value.find('-')
                        if dash >= 0:
                            arch_value = value[:dash]
                            value = value[dash + 1:]
                        dash = value.find('-')
                        if dash >= 0:
                            vendor_value = value[:dash]
                            value = value[dash + 1:]
                        if len(value):
                            os_value = value
                        self.macros[macro] = vorig
                        self.macros[macro + '_cpu'] = arch_value
                        self.macros[macro + '_arch'] = arch_value
                        self.macros[macro + '_vendor'] = vendor_value
                        self.macros[macro + '_os'] = os_value
                        ok = True
                    if ok:
                        s = s.replace(m, '')
                    else:
                        self._error('triplet error: %s' % (' '.join(triplet)))
                    mn = None
                elif m.startswith('%{path '):
                    pl = m[7:-1].strip().split()
                    ok = False
                    result = ''
                    pl_0 = pl[0].lower()
                    if pl_0 == 'prepend':
                        if len(pl) == 2:
                            ok = True
                            p = ' '.join([self._expand(pp) for pp in pl[1:]])
                            if len(self.macros['_pathprepend']):
                                self.macros['_pathprepend'] = \
                                    '%s:%s' % (p, self.macros['_pathprepend'])
                            else:
                                self.macros['_pathprepend'] = p
                    elif pl_0 == 'postpend':
                        if len(pl) == 2:
                            ok = True
                            p = ' '.join([self._expand(pp) for pp in pl[1:]])
                            if len(self.macros['_pathprepend']):
                                self.macros['_pathprepend'] = \
                                    '%s:%s' % (self.macros['_pathprepend'], p)
                            else:
                                self.macros['_pathprepend'] = p
                    elif pl_0 == 'check':
                        if len(pl) == 3:
                            pl_1 = pl[1].lower()
                            p = ' '.join([self._expand(pp) for pp in pl[2:]])
                            if pl_1 == 'exists':
                                ok = True
                                if path.exists(p):
                                    result = '1'
                                else:
                                    result = '0'
                            elif pl_1 == 'isdir':
                                ok = True
                                if path.isdir(p):
                                    result = '1'
                                else:
                                    result = '0'
                            elif pl_1 == 'isfile':
                                ok = True
                                if path.isfile(p):
                                    result = '1'
                                else:
                                    result = '0'
                    if ok:
                        s = s.replace(m, result)
                    else:
                        self._error('path error: %s' % (' '.join(pl)))
                    mn = None
                elif m.startswith('%{pkgconfig '):
                    pcl = m[11:-1].strip().split()
                    if len(pcl):
                        epcl = []
                        for pc in pcl:
                            epcl += [self._expand(pc)]
                        ps = self._pkgconfig(epcl)
                        s = s.replace(m, ps)
                        expanded = True
                    else:
                        self._error('pkgconfig error: %s' % (m[11:-1].strip()))
                    mn = None
                elif m.startswith('%{?') or m.startswith('%{!?'):
                    if m[2] == '!':
                        start = 4
                    else:
                        start = 3
                    colon = m[start:].find(':')
                    if colon < 0:
                        if not m.endswith('}'):
                            log.warning(self._name_line_msg("malformed conditional macro '%s'" % (m)))
                            mn = None
                        else:
                            mn = self._label(m[start:-1])
                    else:
                        mn = self._label(m[start:start + colon])
                    if mn:
                        if m.startswith('%{?'):
                            istrue = False
                            if mn in self.macros:
                                # If defined and 0 or '' then it is false.
                                istrue = _check_bool(self.macros[mn])
                                if istrue is None:
                                    istrue = _check_nil(self.macros[mn])
                            if colon >= 0 and istrue:
                                s = s.replace(m, m[start + colon + 1:-1])
                                expanded = True
                                mn = None
                            elif not istrue:
                                mn = '%{nil}'
                        else:
                            isfalse = True
                            if mn in self.macros:
                                istrue = _check_bool(self.macros[mn])
                                if istrue is None or istrue == True:
                                    isfalse = False
                            if colon >= 0 and isfalse:
                                s = s.replace(m, m[start + colon + 1:-1])
                                expanded = True
                                mn = None
                            else:
                                mn = '%{nil}'
                if mn:
                    if mn.lower() in self.macros:
                        s = s.replace(m, self.macros[mn.lower()])
                        expanded = True
                    elif show_warning:
                        self._error("macro '%s' not found" % (mn))
        return self._shell(s)

    def _disable(self, config, ls):
        if len(ls) != 2:
            log.warning(self._name_line_msg('invalid disable statement'))
        else:
            if ls[1] == 'select':
                self.macros.lock_read_map()
                log.trace('config: %s: %3d:  _disable_select: %s' % (self.name, self.lc,
                                                                     ls[1]))
            else:
                log.warning(self._name_line_msg('invalid disable statement: %s' % (ls[1])))

    def _select(self, config, ls):
        if len(ls) != 2:
            log.warning(self._name_line_msg('invalid select statement'))
        else:
            r = self.macros.set_read_map(ls[1])
            log.trace('config: %s: %3d:  _select: %s %s %r' % \
                          (self.name, self.lc,
                           r, ls[1], self.macros.maps()))

    def _sources(self, ls):
        return sources.process(ls[0][1:], ls[1:], self.macros, self._error)

    def _hash(self, ls):
        return sources.hash(ls[1:], self.macros, self._error)

    def _define(self, config, ls):
        if len(ls) <= 1:
            log.warning(self._name_line_msg('invalid macro definition'))
        else:
            d = self._label(ls[1])
            if self.disable_macro_reassign:
                if (d not in self.macros) or \
                        (d in self.macros and len(self.macros[d]) == 0):
                    if len(ls) == 2:
                        self.macros[d] = '1'
                    else:
                        self.macros[d] = ' '.join([f.strip() for f in ls[2:]])
                else:
                    log.warning(self._name_line_msg("macro '%s' already defined" % (d)))
            else:
                if len(ls) == 2:
                    self.macros[d] = '1'
                else:
                    self.macros[d] = ' '.join([f.strip() for f in ls[2:]])

    def _undefine(self, config, ls):
        if len(ls) <= 1:
            log.warning(self._name_line_msg('invalid macro definition'))
        else:
            mn = self._label(ls[1])
            if mn in self.macros:
                del self.macros[mn]

    def _ifs(self, config, ls, label, iftrue, isvalid, dir, info):
        log.trace('config: %s: %3d:  _ifs[%i]: dir=%s %i %r' % \
                  (self.name, self.lc, self.if_depth, str(dir), len(ls), ls))
        in_dir = dir
        in_iftrue = True
        data = []
        while True:
            if isvalid and \
                    ((iftrue and in_iftrue) or (not iftrue and not in_iftrue)):
                this_isvalid = True
            else:
                this_isvalid = False
            r = self._parse(config, dir, info, roc = True, isvalid = this_isvalid)
            if r[0] == 'package':
                if this_isvalid:
                    dir, info, data = self._process_package(r, dir, info, data)
            elif r[0] == 'control':
                if r[1] == '%end':
                    self._error(label + ' without %endif')
                    raise error.general('terminating build')
                if r[1] == '%endif':
                    log.trace('config: %s: %3d:  _ifs[%i]: %%endif: dir=%s %s %s %r' % \
                              (self.name, self.lc, self.if_depth,
                               str(dir), r[1], this_isvalid, data))
                    if in_dir is None:
                        if dir is not None:
                            dir, info, data = self._process_directive(r, dir, info, data)
                    else:
                        if in_dir != dir:
                            self._error('directives cannot change' \
                                        ' scope across if statements')

                    return data
                if r[1] == '%else':
                    in_iftrue = False
            elif r[0] == 'directive':
                if this_isvalid:
                    if r[1] == '%include':
                        self.load(r[2][0])
                        continue
                    dir, info, data = self._process_directive(r, dir, info, data)
            elif r[0] == 'data':
                if this_isvalid:
                    dir, info, data = self._process_data(r, dir, info, data)
        # @note is a directive extend missing

    def _if(self, config, ls, isvalid, dir, info, invert = False):

        def add(x, y):
            return x + ' ' + str(y)

        if len(ls) == 1:
            self._error('invalid if expression: ' + reduce(add, ls, ''))

        cistrue = True # compound istrue
        sls = reduce(add, ls[1:], '').split()
        cls = sls

        log.trace('config: %s: %3d:  _if[%i]: %s' % (self.name, self.lc,
                                                    self.if_depth, sls))

        self.if_depth += 1

        while len(cls) > 0 and isvalid:

            join_op = 'none'

            if cls[0] == '||' or cls[0] == '&&':
                if cls[0] == '||':
                    join_op = 'or'
                elif cls[0] == '&&':
                    join_op = 'and'
                cls = cls[1:]
                log.trace('config: %s: %3d:  _if[%i]: joining: %s' % \
                          (self.name, self.lc,
                           self.if_depth,
                           join_op))
            ori = 0
            andi = 0
            i = len(cls)
            if '||' in cls:
                ori = cls.index('||')
                log.trace('config: %s: %3d:  _if[%i}: OR found at %i' % \
                          (self.name, self.lc,
                           self.if_depth,
                           ori))
            if '&&' in cls:
                andi = cls.index('&&')
                log.trace('config: %s: %3d:  _if[%i]: AND found at %i' % \
                          (self.name, self.lc,
                           self.if_depth,
                           andi))
            if ori > 0 or andi > 0:
                if ori == 0:
                    i = andi
                elif andi == 0:
                    i = ori
                elif ori < andi:
                    i = andi
                else:
                    i = andi
                log.trace('config: %s: %3d:  _if[%i]: next OP found at %i' % \
                          (self.name, self.lc,
                           self.if_depth,
                           i))
            ls = cls[:i]
            if len(ls) == 0:
                self._error('invalid if expression: ' + reduce(add, sls, ''))
            cls = cls[i:]

            istrue = False

            s = ' '.join(ls)
            ifls = ls

            if len(ifls) == 1:
                #
                # Check if '%if %{x} == %{nil}' has both parts as nothing
                # which means '%if ==' is always True and '%if !=' is always false.
                #
                if ifls[0] == '==':
                    istrue = True
                elif ifls[0] == '!=':
                    istrue = False
                else:
                    istrue = _check_bool(ifls[0])
                    if istrue == None:
                        self._error('invalid if bool value: ' + reduce(add, ls, ''))
                        istrue = False
            elif len(ifls) == 2:
                if ifls[0] == '!':
                    istrue = _check_bool(ifls[1])
                    if istrue == None:
                        self._error('invalid if bool value: ' + reduce(add, ls, ''))
                        istrue = False
                    else:
                        istrue = not istrue
                else:
                    #
                    # Check is something is being checked against empty,
                    #   ie '%if %{x} == %{nil}'
                    # The logic is 'something == nothing' is False and
                    # 'something != nothing' is True.
                    #
                    if ifls[1] == '==':
                        istrue = False
                    elif  ifls[1] == '!=':
                        istrue = True
                    else:
                        self._error('invalid if bool operator: ' + reduce(add, ls, ''))
            else:
                if len(ifls) >= 3:
                    for op in ['==', '!=', '>=', '=>', '=<', '<=', '>', '<']:
                        if op in ifls:
                            op_pos = ifls.index(op)
                            ifls = (' '.join(ifls[:op_pos]), op, ' '.join(ifls[op_pos + 1:]))
                            break
                if len(ifls) != 3:
                     self._error('malformed if: ' + reduce(add, ls, ''))
                if ifls[1] == '==':
                    if ifls[0] == ifls[2]:
                        istrue = True
                    else:
                        istrue = False
                elif ifls[1] == '!=' or ifls[1] == '=!':
                    if ifls[0] != ifls[2]:
                        istrue = True
                    else:
                        istrue = False
                elif ifls[1] == '>':
                    if ifls[0] > ifls[2]:
                        istrue = True
                    else:
                        istrue = False
                elif ifls[1] == '>=' or ifls[1] == '=>':
                    if ifls[0] >= ifls[2]:
                        istrue = True
                    else:
                        istrue = False
                elif ifls[1] == '<=' or ifls[1] == '=<':
                    if ifls[0] <= ifls[2]:
                        istrue = True
                    else:
                        istrue = False
                elif ifls[1] == '<':
                    if ifls[0] < ifls[2]:
                        istrue = True
                    else:
                        istrue = False
                else:
                    self._error('invalid %if operator: ' + reduce(add, ls, ''))

            if join_op == 'or':
                if istrue:
                    cistrue = True
            elif join_op == 'and':
                if not istrue:
                    cistrue = False
            else:
                cistrue = istrue

            log.trace('config: %s: %3d:  _if[%i]:  %s %s %s %s' % (self.name, self.lc,
                                                                   self.if_depth,
                                                                   ifls, str(cistrue),
                                                                   join_op, str(istrue)))

        if invert:
            cistrue = not cistrue

        ifs_return = self._ifs(config, ls, '%if', cistrue, isvalid, dir, info)

        self.if_depth -= 1

        log.trace('config: %s: %3d:  _if[%i]: %r' % (self.name, self.lc,
                                                     self.if_depth, ifs_return))

        return ifs_return

    def _ifos(self, config, ls, isvalid, dir, info):
        isos = False
        if isvalid:
            os = self.define('_os')
            ls = ' '.join(ls).split()
            for l in ls[1:]:
                if l in os:
                    isos = True
                    break
        return self._ifs(config, ls, '%ifos', isos, isvalid, dir, info)

    def _ifnos(self, config, ls, isvalid, dir, info):
        isnos = True
        if isvalid:
            os = self.define('_os')
            ls = ' '.join(ls).split()
            for l in ls[1:]:
                if l in os:
                    isnos = False
                    break
        return self._ifs(config, ls, '%ifnos', isnos, isvalid, dir, info)

    def _ifarch(self, config, positive, ls, isvalid, dir, info):
        isarch = False
        if isvalid:
            arch = self.define('_arch')
            ls = ' '.join(ls).split()
            for l in ls[1:]:
                if l in arch:
                    isarch = True
                    break
        if not positive:
            isarch = not isarch
        return self._ifs(config, ls, '%ifarch', isarch, isvalid, dir, info)

    def _parse(self, config, dir, info, roc = False, isvalid = True):
        # roc = return on control

        def _clean(line):
            line = line[0:-1]
            b = line.find('#')
            if b >= 0:
                line = line[1:b] + ('\\' if line[-1] == '\\' else '')
            return line.strip()

        def _clean_and_pack(line, last_line):
            leading_ws = ' ' if len(line) > 0 and line[0].isspace() else ''
            line = _clean(line)
            if len(last_line) > 0:
                line = last_line + leading_ws + line
            return line

        #
        # Need to add code to count matching '{' and '}' and if they
        # do not match get the next line and add to the string until
        # they match. This closes an opening '{' that is on another
        # line.
        #
        ll = ''
        for l in config:
            self.lc += 1
            l = _clean_and_pack(l, ll)
            if len(l) == 0:
                continue
            if l[-1] == '\\':
                ll = l[0:-1]
                continue
            ll = ''
            if isvalid:
                indicator = '>'
            else:
                indicator = ' '
            log.trace('config: %s: %3d:%s%s [%s]' % \
                          (self.name, self.lc, indicator, l, str(isvalid)))
            lo = l
            if isvalid:
                l = self._expand(l)
            if len(l) == 0:
                continue
            if l[0] == '%':
                ls = self.wss.split(l, 2)
                los = self.wss.split(lo, 2)
                if ls[0] == '%package':
                    if isvalid:
                        if ls[1] == '-n':
                            name = ls[2]
                        else:
                            name = self.name + '-' + ls[1]
                        return ('package', name)
                elif ls[0] == '%disable':
                    if isvalid:
                        self._disable(config, ls)
                elif ls[0] == '%select':
                    if isvalid:
                        self._select(config, ls)
                elif ls[0] == '%source' or ls[0] == '%patch':
                    if isvalid:
                        d = self._sources(ls)
                        if d is not None:
                            return ('data', d)
                elif ls[0] == '%hash':
                    if isvalid:
                        d = self._hash(ls)
                        if d is not None:
                            return ('data', d)
                elif ls[0] == '%patch':
                    if isvalid:
                        self._select(config, ls)
                elif ls[0] == '%error':
                    if isvalid:
                        return ('data', ['%%error %s' % (self._name_line_msg(l[7:]))])
                elif ls[0] == '%log':
                    if isvalid:
                        return ('data', ['%%log %s' % (self._name_line_msg(l[4:]))])
                elif ls[0] == '%warning':
                    if isvalid:
                        return ('data', ['%%warning %s' % (self._name_line_msg(l[9:]))])
                elif ls[0] == '%define' or ls[0] == '%global':
                    if isvalid:
                        self._define(config, ls)
                elif ls[0] == '%undefine':
                    if isvalid:
                        self._undefine(config, ls)
                elif ls[0] == '%if':
                    d = self._if(config, ls, isvalid, dir, info)
                    if len(d):
                        log.trace('config: %s: %3d:  %%if: %s' % (self.name, self.lc, d))
                        return ('data', d)
                elif ls[0] == '%ifn':
                    d = self._if(config, ls, isvalid, dir, info, True)
                    if len(d):
                        log.trace('config: %s: %3d:  %%ifn: %s' % (self.name, self.lc, d))
                        return ('data', d)
                elif ls[0] == '%ifos':
                    d = self._ifos(config, ls, isvalid, dir, info)
                    if len(d):
                        return ('data', d)
                elif ls[0] == '%ifnos':
                    d = self._ifnos(config, ls, isvalid, dir, info)
                    if len(d):
                        return ('data', d)
                elif ls[0] == '%ifarch':
                    d = self._ifarch(config, True, ls, isvalid, dir, info)
                    if len(d):
                        return ('data', d)
                elif ls[0] == '%ifnarch':
                    d = self._ifarch(config, False, ls, isvalid, dir, info)
                    if len(d):
                        return ('data', d)
                elif ls[0] == '%endif':
                    if roc:
                        return ('control', '%endif', '%endif')
                    log.warning(self._name_line_msg("unexpected '" + ls[0] + "'"))
                elif ls[0] == '%else':
                    if roc:
                        return ('control', '%else', '%else')
                    log.warning(self._name_line_msg("unexpected '" + ls[0] + "'"))
                elif ls[0].startswith('%defattr'):
                    return ('data', [l])
                elif ls[0] == '%bcond_with':
                    if isvalid:
                        #
                        # Check if already defined. Would be by the command line or
                        # even a host specific default.
                        #
                        if self._label('with_' + ls[1]) not in self.macros:
                            self._define(config, (ls[0], 'without_' + ls[1]))
                elif ls[0] == '%bcond_without':
                    if isvalid:
                        if self._label('without_' + ls[1]) not in self.macros:
                            self._define(config, (ls[0], 'with_' + ls[1]))
                else:
                    for r in self._ignore:
                        if r.match(ls[0]) is not None:
                            return ('data', [l])
                    if isvalid:
                        for d in self._directive:
                            if ls[0].strip() == d:
                                log.trace('config: %s: %3d:  _parse: directive: %s' % \
                                          (self.name, self.lc, ls[0].strip()))
                                return ('directive', ls[0].strip(), ls[1:])
                        log.warning(self._name_line_msg("unknown directive: '" + \
                                                        ls[0] + "'"))
                        return ('data', [lo])
            else:
                return ('data', [lo])
        return ('control', '%end', '%end')

    def _process_package(self, results, directive, info, data):
        self._set_package(results[1])
        directive = None
        return (directive, info, data)

    def _process_directive(self, results, directive, info, data):
        new_data = []
        if results[1] == '%description':
            new_data = [' '.join(results[2])]
            if len(results[2]) == 0:
                _package = 'main'
            elif len(results[2]) == 1:
                _package = results[2][0]
            else:
                if results[2][0].strip() != '-n':
                    log.warning(self._name_line_msg("unknown directive option: '%s'" % \
                                                    (' '.join(results[2]))))
                _package = results[2][1].strip()
            self._set_package(_package)
        if directive and directive != results[1]:
            self._directive_extend(directive, data)
        directive = results[1]
        data = new_data
        return (directive, info, data)

    def _process_data(self, results, directive, info, data):
        log.trace('config: %s: %3d:  _process_data: result=#%r# ' \
                  'directive=#%s# info=#%r# data=#%r#' % \
                  (self.name, self.lc, results, directive, info, data))
        new_data = []
        for l in results[1]:
            if l.startswith('%error'):
                l = self._expand(l)
                raise error.general('config error: %s' % (l[7:]))
            elif l.startswith('%log'):
                l = self._expand(l)
                log.output(l[4:])
            elif l.startswith('%warning'):
                l = self._expand(l)
                log.warning(self._name_line_msg(l[9:]))
            if not directive:
                l = self._expand(l)
                ls = self.tags.split(l, 1)
                log.trace('config: %s: %3d:  _tag: %s %s' % (self.name, self.lc, l, ls))
                if len(ls) > 1:
                    info = ls[0].lower()
                    if info[-1] == ':':
                        info = info[:-1]
                    info_data = ls[1].strip()
                else:
                    info_data = ls[0].strip()
                if info is not None:
                    self._info_append(info, info_data)
                else:
                    log.warning(self._name_line_msg("invalid format: '%s'" % \
                                                    (info_data[:-1])))
            else:
                l = self._expand(l)
                log.trace('config: %s: %3d:  _data: %s %s' % \
                          (self.name, self.lc, l, new_data))
                new_data.append(l)
        return (directive, info, data + new_data)

    def _set_package(self, _package):
        if self.package == 'main' and \
                self._packages[self.package].name() != None:
            if self._packages[self.package].name() == _package:
                return
        if _package not in self._packages:
            self._packages[_package] = package(_package,
                                               self.define('%{_arch}'),
                                               self)
        self.package = _package

    def _directive_extend(self, dir, data):
        log.trace('config: %s: %3d:  _directive_extend: %s: %r' % \
                  (self.name, self.lc, dir, data))
        self._packages[self.package].directive_extend(dir, data)

    def _info_append(self, info, data):
        self._packages[self.package].info_append(info, data)

    def set_macros(self, macros):
        if macros is None:
            self.macros = opts.defaults
        else:
            self.macros = macros

    def load(self, name):

        def common_end(left, right):
            end = ''
            while len(left) and len(right):
                if left[-1] != right[-1]:
                    return end
                end = left[-1] + end
                left = left[:-1]
                right = right[:-1]
            return end

        if self.load_depth == 0:
            self._packages[self.package] = package(self.package,
                                                   self.define('%{_arch}'),
                                                   self)

        self.load_depth += 1

        save_name = self.name
        save_parent = self.parent
        save_lc = self.lc

        #
        # Locate the config file. Expand any macros then add the
        # extension. Check if the file exists, therefore directly
        # referenced. If not see if the file contains ':' or the path
        # separator. If it does split the path else use the standard config dir
        # path in the defaults.
        #

        exname = self.expand(name)

        #
        # Macro could add an extension.
        #
        if exname.endswith('.cfg'):
            configname = exname
        else:
            configname = '%s.cfg' % (exname)
            name = '%s.cfg' % (name)

        if ':' in configname:
            cfgname = path.basename(configname)
        else:
            cfgname = common_end(configname, name)

        if not path.exists(configname):
            if ':' in configname:
                configdirs = path.dirname(configname).split(':')
            else:
                configdirs = self.define('_configdir').split(':')
            for cp in configdirs:
                configname = path.join(path.abspath(cp), cfgname)
                if path.exists(configname):
                    break
                configname = None
            if configname is None:
                raise error.general('no config file found: %s' % (cfgname))

        try:
            log.trace('config: %s:  _open: %s' % (self.name, path.host(configname)))
            config = open(path.host(configname), 'r')
        except IOError as err:
            raise error.general('error opening config file: %s' % (path.host(configname)))

        self.configpath += [configname]

        self._includes += [configname + ':' + self.parent]
        self.parent = configname

        self.name = self._relative_path(configname)
        self.lc = 0

        try:
            dir = None
            info = None
            data = []
            while True:
                r = self._parse(config, dir, info)
                if r[0] == 'package':
                    dir, info, data = self._process_package(r, dir, info, data)
                elif r[0] == 'control':
                    if r[1] == '%end':
                        break
                    log.warning(self._name_line_msg("unexpected '%s'" % (r[1])))
                elif r[0] == 'directive':
                    if r[1] == '%include':
                        self.load(r[2][0])
                        continue
                    dir, info, data = self._process_directive(r, dir, info, data)
                elif r[0] == 'data':
                    dir, info, data = self._process_data(r, dir, info, data)
                else:
                    self._error("%d: invalid parse state: '%s" % (self.lc, r[0]))
            if dir is not None:
                self._directive_extend(dir, data)
        except:
            config.close()
            raise
        finally:
            config.close()
            self.name = save_name
            self.parent = save_parent
            self.lc = save_lc
            self.load_depth -= 1

    def defined(self, name):
        return name in self.macros

    def define(self, name):
        if name in self.macros:
            d = self.macros[name]
        else:
            n = self._label(name)
            if n in self.macros:
                d = self.macros[n]
            else:
                raise error.general('%d: macro "%s" not found' % (self.lc, name))
        return self._expand(d)

    def set_define(self, name, value):
        self.macros[name] = value

    def expand(self, line):
        if type(line) == list:
            el = []
            for l in line:
                el += [self._expand(l)]
            return el
        return self._expand(line)

    def macro(self, name):
        if name in self.macros:
            return self.macros[name]
        raise error.general('macro "%s" not found' % (name))

    def directive(self, _package, name):
        if _package not in self._packages:
            raise error.general('package "' + _package + '" not found')
        if name not in self._packages[_package].directives:
            raise error.general('directive "' + name + \
                                '" not found in package "' + _package + '"')
        return self._packages[_package].directives[name]

    def abspath(self, rpath):
        return path.abspath(self.define(rpath))

    def packages(self):
        return self._packages

    def includes(self):
        return self._includes

    def file_name(self):
        return self.name

def run():
    import sys
    try:
        #
        # Run where defaults.mc is located
        #
        opts = options.load(sys.argv, defaults = 'defaults.mc')
        log.trace('config: count %d' % (len(opts.config_files())))
        for config_file in opts.config_files():
            s = open(config_file, opts)
            print(s)
            del s
    except error.general as gerr:
        print(gerr)
        sys.exit(1)
    except error.internal as ierr:
        print(ierr)
        sys.exit(1)
    except KeyboardInterrupt:
        log.notice('abort: user terminated')
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    run()
