#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2020 Chris Johns (chrisj@rtems.org)
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
# This code builds a package compiler tool suite given a tool set. A tool
# set lists the various tools. These are specific tool configurations.
#

from __future__ import print_function

import argparse
import copy
import datetime
import os
import sys

try:
    from . import build
    from . import error
    from . import git
    from . import log
    from . import simhost
    from . import version
except KeyboardInterrupt:
    print('abort: user terminated', file=sys.stderr)
    sys.exit(1)
except:
    raise


def unique(l):
    return sorted(list(set(l)))


def filter_deps(deps, ext):
    rdeps = []
    for d in deps:
        ds = d.split(':', 2)
        if ds[0].endswith(ext):
            rdeps += [ds[0] + ':' + ds[1]]
    return sorted(rdeps)


def normalise_paths(includes, root):
    normalised = []
    for inc in unique(includes):
        config, parent = inc.split(':', 2)
        if config.startswith(root):
            config = config[len(root):]
        if parent.startswith(root):
            parent = parent[len(root):]
        normalised += [config + ':' + parent]
    return normalised


def process_dependencies(includes):
    deps = {}
    incs = [i.split(':', 2) for i in includes]
    for config, parent in incs:
        if parent not in deps:
            deps[parent] = []
        for inc in incs:
            if inc[1] == parent:
                deps[parent] += [inc[0]]
    for d in deps:
        deps[d] = unique(deps[d])
    return deps


def includes_str(includes):
    o = []
    deps = [i.split(':', 2) for i in includes]
    ll = max([len(d[1]) for d in deps])
    for d in deps:
        o += ['%*s %s' % (ll, d[1], d[0])]
    return o


def deps_str(deps):

    def print_node(deps, node, level=0, prefix='', indent=''):
        o = []
        if node != 'root':
            level += 1
            if level == 1:
                o += ['']
            o += [prefix + '+-- ' + node]
        if node in deps:
            prefix += indent
            for c, child in enumerate(deps[node], start=1):
                if c < len(deps[node]) and level > 1:
                    indent = '|    '
                else:
                    indent = '     '
                o += print_node(deps, child, level, prefix, indent)
        return o

    return print_node(deps, 'root')


def run(args=sys.argv):
    ec = 0
    output = []
    try:
        #
        # The RSB options support cannot be used because it loads the defaults
        # for the host which we cannot do here.
        #
        description = 'RTEMS Track Dependencies a build set has for all hosts.'

        argsp = argparse.ArgumentParser(prog='sb-dep-check',
                                        description=description)
        argsp.add_argument('--rtems-version',
                           help='Set the RTEMS version.',
                           type=str,
                           default=version.version())
        argsp.add_argument('--list-hosts',
                           help='List the hosts.',
                           action='store_true')
        argsp.add_argument('--list-bsets',
                           help='List the hosts.',
                           action='store_true')
        argsp.add_argument('--output',
                           help='Output file.',
                           type=str,
                           default=None)
        argsp.add_argument('--log',
                           help='Log file.',
                           type=str,
                           default=simhost.log_default('trackdeps'))
        argsp.add_argument('--trace',
                           help='Enable trace logging for debugging.',
                           action='store_true')
        argsp.add_argument(
            '--not-referenced',
            help='Write out the list of config files not referenced.',
            action='store_true')
        argsp.add_argument('bsets', nargs='*', help='Build sets.')

        argopts = argsp.parse_args(args[1:])

        simhost.load_log(argopts.log)
        log.notice('RTEMS Source Builder - Track Dependencies, %s' %
                   (version.string()))
        log.tracing = argopts.trace

        opts = simhost.load_options(args, argopts, extras=['---keep-going'])
        configs = build.get_configs(opts)

        if argopts.list_hosts:
            simhost.list_hosts()
        elif argopts.list_bsets:
            simhost.list_bset_files(opts, configs)
        else:
            all_bsets = simhost.get_bset_files(configs)
            if len(argopts.bsets) == 0:
                bsets = all_bsets
            else:
                bsets = argopts.bsets
            includes = []
            errors = []
            for bset in bsets:
                b = None
                try:
                    for host in simhost.profiles:
                        b = simhost.buildset(bset, configs, opts)
                        b.build(host)
                        includes += b.includes()
                        errors += b.errors()
                        del b
                except error.general as gerr:
                    log.stderr(str(gerr))
                    log.stderr('Build FAILED')
                    if b:
                        includes += b.includes()
                        errors += b.errors()
                b = None
            root = simhost.get_root(configs)
            all_configs = simhost.get_config_files(configs, True)
            includes = normalise_paths(includes, root)
            bsets = filter_deps(includes, '.bset')
            configs = filter_deps(includes, '.cfg')
            deps_tree = deps_str(process_dependencies(bsets + configs))
            bsets = unique([b.split(':', 2)[0] for b in bsets])
            configs = unique([i.split(':', 2)[0] for i in configs])
            not_used_configs = [c for c in all_configs if c not in configs]
            if len(errors) > 0:
                errors = [
                    e.split(':', 2)[0] for e in normalise_paths(errors, root)
                ]
                errs = []
                for e in errors:
                    if e not in bsets + configs:
                        errs += [e]
                errors = errs
            output = [
                'RSB Dependency Tracker', '',
                'Total buildsets: %d' % (len(all_bsets)),
                'Total configs: %d' % (len(all_configs)), ''
            ]
            if len(errors) > 0:
                output += ['Errored File Set (%d):' % (len(errors)),
                           ''] + \
                           errors + \
                           ['']
            if len(configs) > 0:
                output += ['Include Tree(s):',
                           ''] + \
                           deps_tree + \
                           ['']
            if len(bsets) > 0:
                output += ['Buildsets (%d):' % (len(bsets)),
                           ''] + \
                           bsets + \
                           ['']
            if len(configs) > 0:
                output += ['Configurations (%d):' % (len(configs)),
                           ''] + \
                           configs + \
                           ['']
            if argopts.not_referenced and len(not_used_configs) > 0:
                output += ['Not referenced (%d): ' % (len(not_used_configs)),
                           ''] + \
                           not_used_configs
            output = os.linesep.join(output)
            if argopts.output:
                o = open(argopts.output, "w")
                o.write(output)
                o.close
            else:
                print()
                print(output)
    except error.general as gerr:
        log.stderr(str(gerr))
        log.stderr('Build FAILED')
        ec = 1
    except error.internal as ierr:
        log.stderr(str(ierr))
        log.stderr('Internal Build FAILED')
        ec = 1
    except error.exit as eerr:
        pass
    except KeyboardInterrupt:
        log.notice('abort: user terminated')
        ec = 1
    except:
        raise
        log.notice('abort: unknown error')
        ec = 1
    sys.exit(ec)


if __name__ == "__main__":
    run()
