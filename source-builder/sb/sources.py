#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2014 Chris Johns (chrisj@rtems.org)
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
# Manage sources and patches
#

from . import log


def _args(args):
    return [i for s in [ii.split() for ii in args] for i in s]


def _make_key(label, index):
    return '%s%04d' % (label, index)


def add(label, args, macros, error):
    args = _args(args)
    if len(args) < 2:
        error('%%%s requires at least 2 arguments' % (label))
    _map = '%s-%s' % (label, args[0])
    _value = ' '.join(args[1:])
    macros.create_map(_map)
    index = 0
    while True:
        key = _make_key(label, index)
        if key not in macros.map_keys(_map):
            break
        macros.set_read_map(_map)
        value = macros.get_value(key)
        macros.unset_read_map(_map)
        if value == _value:
            error('%%%s duplicate add: %s' % (label, _value))
        index += 1
    macros.set_write_map(_map)
    macros.define(key, _value)
    macros.unset_write_map()
    return None


def set(label, args, macros, error):
    args = _args(args)
    if len(args) < 2:
        error('%%%s set requires at least 2 arguments' % (label))
        return []
    _map = '%s-%s' % (label, args[0])
    macros.create_map(_map)
    key = _make_key(label, 0)
    if key not in macros.map_keys(_map):
        macros.set_write_map(_map)
        macros.define(key, ' '.join(args[1:]))
        macros.unset_write_map()
    return None


def setup(label, args, macros, error):
    args = _args(args)
    if len(args) < 2:
        error('%%%s setup requires at least 2 arguments: %s' %
              (label, ' '.join(args)))
    ss = '%%setup %s %s' % (label, ' '.join(args))
    _map = '%s-%s' % (label, args[0])
    if 'setup' in macros.map_keys(_map):
        error('%%%s already setup source: %s' % (label, ' '.join(args)))
        return []
    macros.set_write_map(_map)
    macros.define('setup', ss)
    macros.unset_write_map()
    return [ss]


def download(label, args, macros, error):
    args = _args(args)
    if len(args) != 1:
        error('%%%s download requires 1 argument: %s' %
              (label, ' '.join(args)))
    ss = '%%setup %s %s -g' % (label, ' '.join(args))
    _map = '%s-%s' % (label, args[0])
    if 'setup' in macros.map_keys(_map):
        error('%%%s already setup source: %s' % (label, ' '.join(args)))
        return []
    macros.set_write_map(_map)
    macros.define('setup', ss)
    macros.unset_write_map()
    return [ss]


def process(label, args, macros, error):
    if label != 'source' and label != 'patch':
        error('invalid source type: %s' % (label))
    args = _args(args)
    log.trace('sources: %s' % (' '.join(args)))
    if args[0] == 'set':
        return set(label, args[1:], macros, error)
    elif args[0] == 'add':
        return add(label, args[1:], macros, error)
    elif args[0] == 'setup':
        return setup(label, args[1:], macros, error)
    elif args[0] == 'download':
        return download(label, args[1:], macros, error)
    error('invalid %%%s command: %s' % (label, args[0]))


def hash(args, macros, error):
    args = _args(args)
    if len(args) != 3:
        error('invalid number of hash args')
        return
    _map = 'hashes'
    _file = macros.expand(args[1])
    new_value = '%s %s' % (args[0], args[2])
    existing_value = get_hash(_file, macros)
    if existing_value is not None:
        if existing_value != new_value:
            error('conflicting hash definitions for: %s' % (args[1]))
            return
    else:
        macros.create_map(_map)
        macros.set_write_map(_map)
        macros.define(_file, new_value)
        macros.unset_write_map()
    return None


def get(label, name, macros, error):
    _map = '%s-%s' % (label, name)
    keys = macros.map_keys(_map)
    if len(keys) == 0:
        error('no %s set: %s (%s)' % (label, name, _map))
        return
    srcs = []
    for s in keys:
        sm = macros.get(s, globals=False, maps=_map)
        if sm is None:
            error('source macro not found: %s in %s (%s)' % (s, name, _map))
        srcs += [sm[2]]
    return srcs


def get_sources(name, macros, error):
    return get('source', name, macros, error)


def get_patches(name, macros, error):
    return get('patch', name, macros, error)


def get_keys(label, name, macros, error):
    _map = '%s-%s' % (label, name)
    return macros.map_keys(_map)


def get_source_keys(name, macros, error):
    return get_keys('source', name, macros, error)


def get_patch_keys(name, macros, error):
    return get_keys('patch', name, macros, error)


def get_names(label, macros, error):
    names = []
    for m in macros.maps():
        if m.startswith('%s-' % (label)):
            names += [m[len('%s-' % (label)):]]
    return names


def get_source_names(macros, error):
    return get_names('source', macros, error)


def get_patch_names(macros, error):
    return get_names('patch', macros, error)


def get_hash(name, macros):
    hash = None
    if name in macros.map_keys('hashes'):
        m1, m2, hash = macros.get(name, globals=False, maps='hashes')
    return hash
