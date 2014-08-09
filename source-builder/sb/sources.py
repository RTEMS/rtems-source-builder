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

import log

def _args(args):
    return [i for s in [ii.split() for ii in args] for i in s]

def add(label, args, macros, error):
    args = _args(args)
    if len(args) < 2:
        error('%%%s requires at least 2 arguments' % (label))
    _map = '%s-%s' % (label, args[0])
    macros.create_map(_map)
    macros.set_write_map(_map)
    index = macros.map_num_keys(_map)
    macros.define('%s%d' % (label, index), ' '.join(args[1:]))
    macros.unset_write_map()
    return None

def set(label, args, macros, error):
    args = _args(args)
    if len(args) < 2:
        error('%%%s requires at least 2 arguments' % (label))
    _map = '%s-%s' % (label, args[0])
    macros.create_map(_map)
    key = '%s0' % (label)
    if key not in macros.map_keys(_map):
        macros.set_write_map(_map)
        macros.define(key, ' '.join(args[1:]))
        macros.unset_write_map()
    return None

def setup(label, args, macros, error):
    args = _args(args)
    if len(args) < 2:
        error('%%%s requires at least 2 arguments: %s' % (label, ' '.join(args)))
    _map = '%s-%s' % (label, args[0])
    return ['%%setup %s %s' % (label, ' '.join(args))]

def process(label, args, macros, error):
    if label != 'source' and label != 'patch':
        error('invalid source type: %s' % (label))
    args = _args(args)
    log.trace('sources: %s' % (' '.join(args)))
    if len(args) < 3:
        error('%%%s requires at least 3 arguments: %s' % (label, ' '.join(args)))
    if args[0] == 'set':
        return set(label, args[1:], macros, error)
    elif args[0] == 'add':
        return add(label, args[1:], macros, error)
    elif args[0] == 'setup':
        return setup(label, args[1:], macros, error)
    error('invalid %%%s command: %s' % (label, args[0]))

def hash(args, macros, error):
    args = _args(args)
    if len(args) != 3:
        error('invalid number of hash args')
    _map = 'hashes'
    _file = macros.expand(args[1])
    if _file in macros.map_keys(_map):
        error('hash already set: %s' % (args[1]))
    macros.create_map(_map)
    macros.set_write_map(_map)
    macros.define(_file, '%s %s' % (args[0], args[2]))
    macros.unset_write_map()
    return None

def get(type_, name, macros, error):
    _map = '%s-%s' % (type_, name)
    keys = macros.map_keys(_map)
    if len(keys) == 0:
        error('no %s set: %s (%s)' % (type_, name, _map))
    srcs = []
    for s in keys:
        sm = macros.get(s, globals = False, maps = _map)
        if sm is None:
            error('source macro not found: %s in %s (%s)' % (s, name, _map))
        srcs += [sm[2]]
    return srcs

def get_sources(name, macros, error):
    return get('source', name, macros, error)

def get_patches(name, macros, error):
    return get('patch', name, macros, error)

def get_names(type_, macros, error):
    names = []
    for m in macros.maps():
        if m.startswith('%s-' % (type_)):
            names += [m[len('%s-' % (type_)):]]
    return names

def get_source_names(macros, error):
    return get_names('source', macros, error)

def get_patch_names(macros, error):
    return get_names('patch', macros, error)

def get_hash(name, macros):
    hash = None
    if name in macros.map_keys('hashes'):
        m1, m2, hash = macros.get(name, globals = False, maps = 'hashes')
    return hash
