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
# This code is based on a tool I wrote to parse RPM spec files in the RTEMS
# project. This is now a configuration file format that has moved away from the
# spec file format to support the specific needs of cross-compiling GCC. This
# module parses a configuration file into Python data types that can be used by
# other software modules.
#

import os
import re
import sys

import defaults
import error
import execute
import log
import path

class package:

    def __init__(self, name, arch):
        self._name = name
        self._arch = arch
        self.directives = {}
        self.infos = {}

    def __str__(self):

        def _dictlist(dl):
            s = ''
            dll = dl.keys()
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

    def directive_extend(self, dir, data):
        if dir not in self.directives:
            self.directives[dir] = []
        for i in range(0, len(data)):
            data[i] = data[i].strip()
        self.directives[dir].extend(data)

    def info_append(self, info, data):
        if info not in self.infos:
            self.infos[info] = []
        self.infos[info].append(data)

    def get_info(self, info):
        if not info in self.infos:
            raise error.general('no %s in package "%s"' % (info, self.name))
        return self.info

    def version(self):
        return self.get_info('Version')

    def extract_info(self, label):
        infos = {}
        for i in self.infos:
            il = i.lower()
            if il.startswith(label):
                if il == label:
                    il = label + '0'
                elif not il[len(label):].isdigit():
                    continue
                infos[il] = self.infos[i]
        return infos

    def find_info(self, label):
        for i in self.infos:
            if i.lower() == label:
                return self.infos[i]
        return None

    def find_directive(self, label):
        for d in self.directives:
            if d.lower() == label:
                return self.directives[d]
        return None

    def name(self):
        info = self.find_info('name')
        if info:
            return info[0]
        return self._name

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
        return self.extract_info('source');

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

    def post(self):
        return self.find_directive('%post')

    def include(self):
        return self.find_directive('%include')

    def long_name(self):
        return self.name()

class file:
    """Parse a config file."""

    _directive = [ '%description',
                   '%changelog',
                   '%prep',
                   '%build',
                   '%check',
                   '%include',
                   '%install',
                   '%clean',
                   '%post',
                   '%preun',
                   '%files' ]

    _ignore = [ re.compile('%setup'),
                re.compile('%configure'),
                re.compile('%source[0-9]*'),
                re.compile('%patch[0-9]*') ]

    def __init__(self, name, _defaults, opts):
        self.opts = opts
        if self.opts.trace():
            print 'config: %s' % (name)
        self.configpath = []
        self.wss = re.compile(r'\s+')
        self.tags = re.compile(r':+')
        self.sf = re.compile(r'%\([^\)]+\)')
        self.default_defines = {}
        for d in _defaults:
            self.default_defines[self._label(d)] = _defaults[d][2]
        for arg in self.opts.args:
            if arg.startswith('--with-') or arg.startswith('--without-'):
                label = arg[2:].lower().replace('-', '_')
                self.default_defines[self._label(label)] = label
        self.load_depth = 0
        self.load(name)

    def __str__(self):

        def _dict(dd):
            s = ''
            ddl = dd.keys()
            ddl.sort()
            for d in ddl:
                s += '  ' + d + ': ' + dd[d] + '\n'
            return s

        s = 'config: %s' % ('.'.join(self.configpath)) + \
            '\n' + str(self.opts) + \
            '\nlines parsed: %d' % (self.lc) + \
            '\nname: ' + self.name + \
            '\ndefines:\n' + _dict(self.defines)
        for _package in self._packages:
            s += str(self._packages[_package])
        return s

    def _name_line_msg(self,  msg):
        return '%s:%d: %s' % (path.basename(self.name), self.lc,  msg)

    def _output(self, text):
        if not self.opts.quiet():
            log.output(text)

    def _warning(self, msg):
        self._output('warning: %s' % (self._name_line_msg(msg)))

    def _error(self, msg):
        err = 'error: %s' % (self._name_line_msg(msg))
        print >> sys.stderr, err
        self._output(err)
        self.in_error = True
        if not self.opts.dry_run():
            print >> sys.stderr, 'warning: switched to dry run due to errors'
            self.opts.set_dry_run()

    def _label(self, name):
        return '%{' + name.lower() + '}'

    def _macro_split(self, s):
        '''Split the string (s) up by macros. Only split on the
           outter level. Nested levels will need to split with futher calls.'''
        trace_me = False
        macros = []
        nesting = []
        has_braces = False
        c = 0
        while c < len(s):
            if trace_me:
                print 'ms:', c, '"' + s[c:] + '"', has_braces, len(nesting), nesting
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
            print 'ms:', macros
        return macros

    def _shell(self, line):
        sl = self.sf.findall(line)
        if len(sl):
            e = execute.capture_execution()
            for s in sl:
                exit_code, proc, output = e.shell(s[2:-1])
                if exit_code == 0:
                    line = line.replace(s, output)
                else:
                    raise error.general('shell macro failed: %s: %s' % (s, output))
        return line

    def _expand(self, s):
        expanded = True
        while expanded:
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
                        self._warning('malformed expand macro, no colon found')
                    else:
                        e = self._expand(m[colon + 1:-1].strip())
                        s = s.replace(m, e)
                        expanded = True
                        mn = None
                elif m.startswith('%{with '):
                    #
                    # Change the ' ' to '_' because the macros have no spaces.
                    #
                    n = self._label('with_' + m[7:-1].strip())
                    if n in self.defines:
                        s = s.replace(m, '1')
                    else:
                        s = s.replace(m, '0')
                    expanded = True
                    mn = None
                elif m.startswith('%{echo'):
                    mn = None
                elif m.startswith('%{defined'):
                    n = self._label(m[9:-1].strip())
                    if n in self.defines:
                        s = s.replace(m, '1')
                    else:
                        s = s.replace(m, '0')
                    expanded = True
                    mn = None
                elif m.startswith('%{?') or m.startswith('%{!?'):
                    if m[2] == '!':
                        start = 4
                    else:
                        start = 3
                    colon = m[start:].find(':')
                    if colon < 0:
                        if not m.endswith('}'):
                            self._warning("malform conditional macro '%s'" % (m))
                            mn = None
                        else:
                            mn = self._label(m[start:-1])
                    else:
                        mn = self._label(m[start:start + colon])
                    if mn:
                        if m.startswith('%{?'):
                            if mn in self.defines:
                                if colon >= 0:
                                    s = s.replace(m, m[start + colon + 1:-1])
                                    expanded = True
                                    mn = None
                            else:
                                mn = '%{nil}'
                        else:
                            if mn not in self.defines:
                                if colon >= 0:
                                    s = s.replace(m, m[start + colon + 1:-1])
                                    expanded = True
                                    mn = None
                            else:
                                mn = '%{nil}'
                if mn:
                    if mn.lower() in self.defines:
                        s = s.replace(m, self.defines[mn.lower()])
                        expanded = True
                    elif show_warning:
                        self._error("macro '%s' not found" % (mn))
        return self._shell(s)

    def _define(self, config, ls):
        if len(ls) <= 1:
            self._warning('invalid macro definition')
        else:
            d = self._label(ls[1])
            if (d not in self.defines) or \
                    (d in self.defines and len(self.defines[d]) == 0):
                if len(ls) == 2:
                    self.defines[d] = '1'
                else:
                    self.defines[d] = ls[2].strip()
            else:
                if self.opts.warn_all():
                    self._warning("macro '%s' already defined" % (d))

    def _undefine(self, config, ls):
        if len(ls) <= 1:
            self._warning('invalid macro definition')
        else:
            mn = self._label(ls[1])
            if mn in self.defines:
                self._error("macro '%s' not defined" % (mn))
            del self.defines[mn]

    def _ifs(self, config, ls, label, iftrue, isvalid):
        text = []
        in_iftrue = True
        while True:
            if isvalid and \
                    ((iftrue and in_iftrue) or (not iftrue and not in_iftrue)):
                this_isvalid = True
            else:
                this_isvalid = False
            r = self._parse(config, roc = True, isvalid = this_isvalid)
            if r[0] == 'control':
                if r[1] == '%end':
                    self._error(label + ' without %endif')
                    raise error.general('terminating build')
                if r[1] == '%endif':
                    return text
                if r[1] == '%else':
                    in_iftrue = False
            elif r[0] == 'data':
                if this_isvalid:
                    text.extend(r[1])

    def _if(self, config, ls, isvalid, invert = False):

        def add(x, y):
            return x + ' ' + str(y)

        def check_bool(value):
            if value.isdigit():
                if int(value) == 0:
                    istrue = False
                else:
                    istrue = True
            else:
                istrue = None
            return istrue

        istrue = False
        if isvalid:
            if len(ls) == 2:
                s = ls[1]
            else:
                s = (ls[1] + ' ' + ls[2])
            ifls = s.split()
            if len(ifls) == 1:
                #
                # Check if '%if %{x} == %{nil}' has both parts as nothing
                # which means '%if ==' is always True and '%if !=' is always false.
                #
                if ifls[0] == '==':
                    istrue = True
                elif ifls[0] == '==':
                    istrue = False
                else:
                    istrue = check_bool(ifls[0])
                    if istrue == None:
                        self._error('invalid if bool value: ' + reduce(add, ls, ''))
                        istrue = False
            elif len(ifls) == 2:
                if ifls[0] == '!':
                    istrue = check_bool(ifls[1])
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
            elif len(ifls) == 3:
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
            else:
                self._error('malformed if: ' + reduce(add, ls, ''))
            if invert:
                istrue = not istrue
            if self.opts.trace():
                print '_if:  ', ifls, istrue
        return self._ifs(config, ls, '%if', istrue, isvalid)

    def _ifos(self, config, ls, isvalid):
        isos = False
        if isvalid:
            os = self.define('_os')
            if ls[0].find(os) >= 0 or ls[1].find(os) >= 0:
                isos = True
            else:
                isos = False
        return self._ifs(config, ls, '%ifos', isos, isvalid)

    def _ifarch(self, config, positive, ls, isvalid):
        isarch = False
        if isvalid:
            arch = self.define('_arch')
            if ls[0].find(arch) >= 0 or ls[1].find(arch) >= 0:
                isarch = True
            else:
                isarch = False
        if not positive:
            isarch = not isarch
        return self._ifs(config, ls, '%ifarch', isarch, isvalid)

    def _parse(self, config, roc = False, isvalid = True):
        # roc = return on control

        def _clean(line):
            line = line[0:-1]
            b = line.find('#')
            if b >= 0:
                line = line[1:b]
            return line.strip()

        #
        # Need to add code to count matching '{' and '}' and if they
        # do not match get the next line and add to the string until
        # they match. This closes an opening '{' that is on another
        # line.
        #

        for l in config:
            self.lc += 1
            l = _clean(l)
            if len(l) == 0:
                continue
            if self.opts.trace():
                print '%03d: %d %s' % (self.lc, isvalid, l)
            if isvalid:
                l = self._expand(l)
            if len(l) == 0:
                continue
            if l[0] == '%':
                ls = self.wss.split(l, 2)
                if ls[0] == '%package':
                    if isvalid:
                        if ls[1] == '-n':
                            name = ls[2]
                        else:
                            name = self.name + '-' + ls[1]
                        return ('package', name)
                elif ls[0] == '%error':
                    if isvalid:
                        return ('data', ['%%error %s' % (self._name_line_msg(l[7:]))])
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
                    d = self._if(config, ls, isvalid)
                    if len(d):
                        return ('data', d)
                elif ls[0] == '%ifn':
                    d = self._if(config, ls, isvalid, True)
                    if len(d):
                        return ('data', d)
                elif ls[0] == '%ifos':
                    d = self._ifos(config, ls, isvalid)
                    if len(d):
                        return ('data', d)
                elif ls[0] == '%ifarch':
                    d = self._ifarch(config, True, ls, isvalid)
                    if len(d):
                        return ('data', d)
                elif ls[0] == '%ifnarch':
                    d = self._ifarch(config, False, ls, isvalid)
                    if len(d):
                        return ('data', d)
                elif ls[0] == '%endif':
                    if roc:
                        return ('control', '%endif')
                    self._warning("unexpected '" + ls[0] + "'")
                elif ls[0] == '%else':
                    if roc:
                        return ('control', '%else')
                    self._warning("unexpected '" + ls[0] + "'")
                elif ls[0].startswith('%defattr'):
                    return ('data', [l])
                elif ls[0] == '%bcond_with':
                    if isvalid:
                        #
                        # Check if already defined. Would be by the command line or
                        # even a host specific default.
                        #
                        if self._label('with_' + ls[1]) not in self.defines:
                            self._define(config, (ls[0], 'without_' + ls[1]))
                elif ls[0] == '%bcond_without':
                    if isvalid:
                        if self._label('without_' + ls[1]) not in self.defines:
                            self._define(config, (ls[0], 'with_' + ls[1]))
                else:
                    for r in self._ignore:
                        if r.match(ls[0]) is not None:
                            return ('data', [l])
                    if isvalid:
                        for d in self._directive:
                            if ls[0].strip() == d:
                                return ('directive', ls[0].strip(), ls[1:])
                        self._warning("unknown directive: '" + ls[0] + "'")
                        return ('data', [l])
            else:
                return ('data', [l])
        return ('control', '%end')

    def _set_package(self, _package):
        if self.package == 'main' and \
                self._packages[self.package].name() != None:
            if self._packages[self.package].name() == _package:
                return
        if _package not in self._packages:
            self._packages[_package] = package(_package,
                                               self.define('%{_arch}'))
        self.package = _package

    def _directive_extend(self, dir, data):
        self._packages[self.package].directive_extend(dir, data)

    def _info_append(self, info, data):
        self._packages[self.package].info_append(info, data)

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
            self.in_error = False
            self.lc = 0
            self.name = name
            self.defines = self.default_defines
            self.conditionals = {}
            self._packages = {}
            self.package = 'main'
            self._packages[self.package] = package(self.package,
                                                   self.define('%{_arch}'))

        self.load_depth += 1

        save_name = self.name
        save_lc = self.lc

        self.name = name
        self.lc = 0

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
            if self.opts.trace():
                print '_open: %s' % (path.host(configname))
            config = open(path.host(configname), 'r')
        except IOError, err:
            raise error.general('error opening config file: %s' % (path.host(configname)))
        self.configpath += [configname]

        try:
            dir = None
            data = []
            while True:
                r = self._parse(config)
                if r[0] == 'package':
                    self._set_package(r[1])
                    dir = None
                elif r[0] == 'control':
                    if r[1] == '%end':
                        break
                    self._warning("unexpected '" + r[1] + "'")
                elif r[0] == 'directive':
                    new_data = []
                    if r[1] == '%description':
                        new_data = [' '.join(r[2])]
                    elif r[1] == '%include':
                        self.load(r[2][0])
                        continue
                    else:
                        if len(r[2]) == 0:
                            _package = 'main'
                        elif len(r[2]) == 1:
                            _package = r[2][0]
                        else:
                            if r[2][0].strip() != '-n':
                                self._warning("unknown directive option: '%s'" % (' '.join(r[2])))
                            _package = r[2][1].strip()
                        self._set_package(_package)
                    if dir and dir != r[1]:
                        self._directive_extend(dir, data)
                    dir = r[1]
                    data = new_data
                elif r[0] == 'data':
                    for l in r[1]:
                        l = self._expand(l)
                        if l.startswith('%error'):
                            raise error.general('config error: %s' % (l[7:]))
                        elif l.startswith('%warning'):
                            print >> sys.stderr, 'warning: %s' % (l[9:])
                            self._warning(l[9:])
                        if not dir:
                            ls = self.tags.split(l, 1)
                            if self.opts.trace():
                                print '_tag: ', l, ls
                            if len(ls) > 1:
                                i = ls[0]
                                self._info_append(i, ls[1].strip())
                                # It seems like the info's also appear as
                                # defines or can be accessed via macros.
                                if ls[0][len(ls[0]) - 1] == ':':
                                    ls[0] = ls[0][:-1]
                                ls[0] = ls[0].lower()
                                self._define(None, ('', ls[0], ls[1]))
                            else:
                                self._warning("invalid format: '" + l[:-1] + "'")
                        else:
                            data.append(l)
                else:
                    self._error("invalid parse state: '" + r[0] + "'")
            if dir is not None:
                self._directive_extend(dir, data)
        except:
            config.close()
            raise

        config.close()

        self.name = save_name
        self.lc = save_lc

        self.load_depth -= 1

    def define(self, name):
        if name.lower() in self.defines:
            d = self.defines[name.lower()]
        else:
            n = self._label(name)
            if n in self.defines:
                d = self.defines[n]
            else:
                raise error.general('macro "' + name + '" not found')
        return self._expand(d)

    def set_define(self, name, value):
        self.defines[name.lower()] = value

    def expand(self, line):
        return self._expand(line)

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

def run():
    import sys
    try:
        opts, _defaults = defaults.load(sys.argv)
        if opts.trace():
            print 'config: count %d' % (len(opts.config_files()))
        for config_file in opts.config_files():
            s = file(config_file, _defaults = _defaults, opts = opts)
            print s
            del s
    except error.general, gerr:
        print gerr
        sys.exit(1)
    except error.internal, ierr:
        print ierr
        sys.exit(1)
    except KeyboardInterrupt:
        print 'user terminated'
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    run()
