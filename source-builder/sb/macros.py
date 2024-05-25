#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2013 Chris Johns (chrisj@rtems.org)
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
# Macro tables.
#

from __future__ import print_function

import re
import os
import string

from . import error
from . import path


#
# Macro tables
#
class macros:

    class macro_iterator:

        def __init__(self, keys):
            self.keys = keys
            self.index = 0

        def __iter__(self):
            return self

        def __next__(self):
            if self.index < len(self.keys):
                key = self.keys[self.index]
                self.index += 1
                return key
            raise StopIteration

        def iterkeys(self):
            return self.keys

    @staticmethod
    def _unicode_to_str(us):
        try:
            if type(us) == unicode:
                return us.encode('ascii', 'replace')
        except:
            pass
        try:
            if type(us) == bytes:
                return us.encode('ascii', 'replace')
        except:
            pass
        return us

    def __init__(self, name=None, original=None, sbdir='.'):
        self.files = []
        self.macro_filter = re.compile(r'%{[^}]+}')
        if original is None:
            self.macros = {}
            self.read_maps = []
            self.read_map_locked = False
            self.write_map = 'global'
            self.macros['global'] = {}
            self.macros['global']['_cwd'] = ('dir', 'required',
                                             path.abspath(os.getcwd()))
            self.macros['global']['_sbdir'] = ('dir', 'required',
                                               path.abspath(sbdir))
            self.macros['global']['_sbtop'] = ('dir', 'required',
                                               path.abspath(
                                                   path.dirname(sbdir)))
        else:
            self.macros = {}
            for m in original.macros:
                if m not in self.macros:
                    self.macros[m] = {}
                for k in original.macros[m]:
                    self.macros[m][k] = original.macros[m][k]
            self.read_maps = sorted(original.read_maps)
            self.read_map_locked = original.read_map_locked
            self.write_map = original.write_map
        if name is not None:
            self.load(name)

    def __copy__(self):
        return macros(original=self)

    def __str__(self):
        text_len = 80
        text = ''
        for f in self.files:
            text += '> %s%s' % (f, os.linesep)
        maps = sorted(self.macros)
        maps.remove('global')
        maps += ['global']
        for map in maps:
            text += '[%s]%s' % (map, os.linesep)
            for k in sorted(self.macros[map].keys()):
                d = self.macros[map][k]
                text += " %s:%s '%s'%s '%s'%s" % \
                    (k, ' ' * (20 - len(k)),
                     d[0], ' ' * (8 - len(d[0])),
                     d[1], ' ' * (10 - len(d[1])))
                if len(d[2]) == 0:
                    text += "''%s" % (os.linesep)
                else:
                    if '\n' in d[2]:
                        text += "'''"
                    else:
                        text += "'"
                indent = False
                ds = d[2].split('\n')
                lc = 0
                for l in ds:
                    lc += 1
                    l = self._unicode_to_str(l)
                    while len(l):
                        if indent:
                            text += ' %21s %10s %12s' % (' ', ' ', ' ')
                        text += l[0:text_len]
                        l = l[text_len:]
                        if len(l):
                            text += ' \\'
                        elif lc == len(ds):
                            if len(ds) > 1:
                                text += "'''"
                            else:
                                text += "'"
                        text += '%s' % (os.linesep)
                        indent = True
        return text

    def __iter__(self):
        return macros.macro_iterator(list(self.keys()))

    def __getitem__(self, key):
        macro = self.get(key)
        if macro is None or macro[1] == 'undefine':
            raise IndexError('key: %s' % (key))
        return macro[2]

    def __setitem__(self, key, value):
        key = self._unicode_to_str(key)
        if type(key) is not str:
            raise TypeError('bad key type (want str): %s (%s)' %
                            (type(key), key))
        if type(value) is not tuple:
            value = self._unicode_to_str(value)
        if type(value) is str:
            value = ('none', 'none', value)
        if type(value) is not tuple:
            raise TypeError('bad value type (want tuple): %s' % (type(value)))
        if len(value) != 3:
            raise TypeError('bad value tuple (len not 3): %d' % (len(value)))
        value = (self._unicode_to_str(value[0]),
                 self._unicode_to_str(value[1]),
                 self._unicode_to_str(value[2]))
        if type(value[0]) is not str:
            raise TypeError('bad value tuple type field: %s' %
                            (type(value[0])))
        if type(value[1]) is not str:
            raise TypeError('bad value tuple attrib field: %s' %
                            (type(value[1])))
        if type(value[2]) is not str:
            raise TypeError('bad value tuple value field: %s' %
                            (type(value[2])))
        if value[0] not in ['none', 'triplet', 'dir', 'file', 'exe']:
            raise TypeError('bad value tuple (type field): %s' % (value[0]))
        if value[1] not in [
                'none', 'optional', 'required', 'override', 'undefine',
                'convert'
        ]:
            raise TypeError('bad value tuple (attrib field): %s' % (value[1]))
        if value[1] == 'convert':
            value = (value[0], value[1], self.expand(value[2]))
        self.macros[self.write_map][self.key_filter(key)] = value

    def __delitem__(self, key):
        self.undefine(key)

    def __contains__(self, key):
        return self.has_key(self._unicode_to_str(key))

    def __len__(self):
        return len(list(self.keys()))

    def keys(self, globals=True):
        if globals:
            keys = list(self.macros['global'].keys())
        else:
            keys = []
        for rm in self.get_read_maps():
            for mk in self.macros[rm]:
                if self.macros[rm][mk][1] == 'undefine':
                    if mk in keys:
                        keys.remove(mk)
                else:
                    keys.append(mk)
        return sorted(set(keys))

    def has_key(self, key):
        key = self._unicode_to_str(key)
        if type(key) is not str:
            raise TypeError('bad key type (want str): %s' % (type(key)))
        if self.key_filter(key) not in list(self.keys()):
            return False
        return True

    def create_map(self, _map):
        if _map not in self.macros:
            self.macros[_map] = {}

    def delete_map(self, _map):
        if _map in self.macros:
            self.macros.pop(_map, None)

    def maps(self):
        return list(self.macros.keys())

    def map_keys(self, _map):
        if _map in self.macros:
            return sorted(self.macros[_map].keys())
        return []

    def map_num_keys(self, _map):
        return len(self.map_keys(_map))

    def get_read_maps(self):
        return [rm[5:] for rm in self.read_maps]

    def key_filter(self, key):
        if key.startswith('%{') and key[-1] == '}':
            key = key[2:-1]
        return key.lower()

    def parse(self, lines):

        def _clean(l):
            if '#' in l:
                l = l[:l.index('#')]
            if '\r' in l:
                l = l[:l.index('r')]
            if '\n' in l:
                l = l[:l.index('\n')]
            return l.strip()

        trace_me = False
        if trace_me:
            print('[[[[]]]] parsing macros')
        macros = {'global': {}}
        map = 'global'
        lc = 0
        state = 'key'
        token = ''
        macro = []
        for l in lines:
            lc += 1
            #print 'l:%s' % (l[:-1])
            if len(l) == 0:
                continue
            l = self._unicode_to_str(l)
            l_remaining = l
            for c in l:
                if trace_me:
                    print(']]]]]]]] c:%s(%d) s:%s t:"%s" m:%r M:%s' % \
                        (c, ord(c), state, token, macro, map))
                l_remaining = l_remaining[1:]
                if c == '#' and not state.startswith('value'):
                    break
                if c == '\n' or c == '\r':
                    if not (state == 'key' and len(token) == 0) and \
                            not state.startswith('value-multiline'):
                        raise error.general('malformed macro line:%d: %s' %
                                            (lc, l))
                if state == 'key':
                    if c not in string.whitespace:
                        if c == '[':
                            state = 'map'
                        elif c == '%':
                            state = 'directive'
                        elif c == ':':
                            macro += [token]
                            token = ''
                            state = 'attribs'
                        elif c == '#':
                            break
                        else:
                            token += c
                elif state == 'map':
                    if c == ']':
                        if token not in macros:
                            macros[token] = {}
                        map = token
                        token = ''
                        state = 'key'
                    elif c in string.printable and c not in string.whitespace:
                        token += c
                    else:
                        raise error.general('invalid macro map:%d: %s' %
                                            (lc, l))
                elif state == 'directive':
                    if c in string.whitespace:
                        if token == 'include':
                            self.load(_clean(l_remaining))
                            token = ''
                            state = 'key'
                            break
                    elif c in string.printable and c not in string.whitespace:
                        token += c
                    else:
                        raise error.general('invalid macro directive:%d: %s' %
                                            (lc, l))
                elif state == 'include':
                    if c is string.whitespace:
                        if token == 'include':
                            state = 'include'
                    elif c in string.printable and c not in string.whitespace:
                        token += c
                    else:
                        raise error.general('invalid macro directive:%d: %s' %
                                            (lc, l))
                elif state == 'attribs':
                    if c not in string.whitespace:
                        if c == ',':
                            macro += [token]
                            token = ''
                            if len(macro) == 3:
                                state = 'value-start'
                        else:
                            token += c
                elif state == 'value-start':
                    if c == "'":
                        state = 'value-line-start'
                elif state == 'value-line-start':
                    if c == "'":
                        state = 'value-multiline-start'
                    else:
                        state = 'value-line'
                        token += c
                elif state == 'value-multiline-start':
                    if c == "'":
                        state = 'value-multiline'
                    else:
                        macro += [token]
                        state = 'macro'
                elif state == 'value-line':
                    if c == "'":
                        macro += [token]
                        state = 'macro'
                    else:
                        token += c
                elif state == 'value-multiline':
                    if c == "'":
                        state = 'value-multiline-end'
                    else:
                        token += c
                elif state == 'value-multiline-end':
                    if c == "'":
                        state = 'value-multiline-end-end'
                    else:
                        state = 'value-multiline'
                        token += "'" + c
                elif state == 'value-multiline-end-end':
                    if c == "'":
                        macro += [token]
                        state = 'macro'
                    else:
                        state = 'value-multiline'
                        token += "''" + c
                else:
                    raise error.internal('bad state: %s' % (state))
                if state == 'macro':
                    macros[map][self._unicode_to_str(macro[0].lower())] = \
                                (self._unicode_to_str(macro[1]),
                                 self._unicode_to_str(macro[2]),
                                 self._unicode_to_str(macro[3]))
                    macro = []
                    token = ''
                    state = 'key'
        for m in macros:
            if m not in self.macros:
                self.macros[m] = {}
            for mm in macros[m]:
                self.macros[m][mm] = macros[m][mm]

    def load(self, name):
        names = self.expand(name).split(':')
        for n in names:
            if path.exists(n):
                try:
                    mc = open(path.host(n), 'r')
                    macros = self.parse(mc)
                    mc.close()
                    self.files += [n]
                    return
                except IOError as err:
                    pass
        raise error.general('opening macro file: %s' % \
                                (path.host(self.expand(name))))

    def get(self, key, globals=True, maps=None):
        key = self._unicode_to_str(key)
        if type(key) is not str:
            raise TypeError('bad key type: %s' % (type(key)))
        key = self.key_filter(key)
        if maps is None:
            maps = self.get_read_maps()
        else:
            if type(maps) is str:
                maps = [maps]
            if type(maps) != list:
                raise TypeError('bad maps type: %s' % (type(map)))
        for rm in maps:
            if key in self.macros[rm]:
                return self.macros[rm][key]
        if globals and key in self.macros['global']:
            return self.macros['global'][key]
        return None

    def get_type(self, key):
        m = self.get(key)
        if m is None:
            return None
        return m[0]

    def get_attribute(self, key):
        m = self.get(key)
        if m is None:
            return None
        return m[1]

    def get_value(self, key):
        m = self.get(key)
        if m is None:
            return None
        return m[2]

    def overridden(self, key):
        return self.get_attribute(key) == 'override'

    def define(self, key, value='1'):
        self.__setitem__(key, ('none', 'none', value))

    def undefine(self, key):
        key = self._unicode_to_str(key)
        if type(key) is not str:
            raise TypeError('bad key type: %s' % (type(key)))
        key = self.key_filter(key)
        for map in self.macros:
            if key in self.macros[map]:
                del self.macros[map][key]

    def defined(self, key, globals=True, maps=None):
        return self.get(key, globals, maps) is not None

    def expand(self, _str):
        """Simple basic expander of config file macros."""
        _str = self._unicode_to_str(_str)
        expanded = True
        while expanded:
            expanded = False
            for m in self.macro_filter.findall(_str):
                name = m[2:-1]
                macro = self.get(name)
                if macro is None:
                    raise error.general(
                        'cannot expand default macro: %s in "%s"' % (m, _str))
                _str = _str.replace(m, macro[2])
                expanded = True
        return _str

    def find(self, regex, globals=True):
        what = re.compile(regex)
        keys = []
        for key in self.keys(globals):
            if what.match(key):
                keys += [key]
        return keys

    def set_read_map(self, _map):
        if not self.read_map_locked:
            if _map in self.macros:
                if _map not in self.get_read_maps():
                    rm = '%04d_%s' % (len(self.read_maps), _map)
                    self.read_maps = sorted(self.read_maps + [rm])
                return True
        return False

    def unset_read_map(self, _map):
        if not self.read_map_locked:
            if _map in self.get_read_maps():
                for i in range(0, len(self.read_maps)):
                    if '%04d_%s' % (i, _map) == self.read_maps[i]:
                        self.read_maps.pop(i)
                return True
        return False

    def set_write_map(self, map):
        if map in self.macros:
            self.write_map = map
            return True
        return False

    def unset_write_map(self):
        self.write_map = 'global'

    def lock_read_map(self):
        self.read_map_locked = True

    def unlock_read_map(self):
        self.read_map_locked = False


if __name__ == "__main__":
    import copy
    import sys
    m = macros()
    d = copy.copy(m)
    m['test1'] = 'something'
    if 'test1' in d:
        print('error: copy failed.')
        sys.exit(1)
    m.parse("[test]\n" \
            "test1: none, undefine, ''\n" \
            "name:  none, override, 'pink'\n")
    print('set test:', m.set_read_map('test'))
    if m['name'] != 'pink':
        print('error: override failed. name is %s' % (m['name']))
        sys.exit(1)
    if 'test1' in m:
        print('error: map undefine failed.')
        sys.exit(1)
    print('unset test:', m.unset_read_map('test'))
    print(m)
    print(list(m.keys()))
