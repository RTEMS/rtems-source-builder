#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2019 Chris Johns (chrisj@rtems.org)
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
import json
import os
import sys

try:
    from . import build
    from . import error
    from . import log
    from . import path
    from . import simhost
    from . import version
except KeyboardInterrupt:
    print('abort: user terminated', file=sys.stderr)
    sys.exit(1)
except:
    raise


def process_sources(isources):

    def remove(key, record):
        if key in record:
            del record[key]

    urls = {}
    osources = []
    for src in isources:
        if src['url'] not in urls:
            remove('local', src)
            remove('local_prefix', src)
            remove('compressed', src)
            remove('script', src)
            osources += [src]
            urls[src['url']] = True
    return sorted(osources, key=lambda src: src['file'])


def process_hashes(ihashes):
    files = {}
    ohashes = []

    for hsh in ihashes:
        hs = hsh.replace('  ', ' ').split(' ')
        if len(hs) == 3:
            if hs[1] not in files:
                ohashes += [{'type': hs[0], 'file': hs[1], 'hash': hs[2]}]
                files[hs[1]] = True
    return sorted(ohashes, key=lambda hsh: hsh['file'])


def run(args=sys.argv):
    ec = 0
    get_sources_error = True
    try:
        #
        # The RSB options support cannot be used because it loads the defaults
        # for the host which we cannot do here.
        #
        description = 'RTEMS Get Sources downloads all the source a build set '
        description += 'references for all hosts.'

        argsp = argparse.ArgumentParser(prog='rtems-get-sources',
                                        description=description)
        argsp.add_argument('--rtems-version',
                           help='Set the RTEMS version.',
                           type=str,
                           default=version.version())
        argsp.add_argument('--list-hosts',
                           help='List the hosts.',
                           action='store_true')
        argsp.add_argument('--list-bsets',
                           help='List the buildsets.',
                           action='store_true')
        argsp.add_argument('--list-root-bsets',
                           help='List the toplevel or root buildsets.',
                           action='store_true')
        argsp.add_argument('--download-dir',
                           help='Download directory.',
                           type=str)
        argsp.add_argument('--no-download',
                           help='No downloads.',
                           action='store_true')
        argsp.add_argument('--clean',
                           help='Clean the download directory.',
                           action='store_true')
        argsp.add_argument('--tar',
                           help='Create a tarball of all the source.',
                           action='store_true')
        argsp.add_argument('--log',
                           help='Log file.',
                           type=str,
                           default=simhost.log_default('getsource'))
        argsp.add_argument('--keep-going',
                           help='Keep going on error.',
                           action='store_false',
                           default=True)
        argsp.add_argument('--trace',
                           help='Enable trace logging for debugging.',
                           action='store_true')
        argsp.add_argument('--used',
                           help='Save the used buildset and config files.',
                           type=str,
                           default=None)
        argsp.add_argument('--unused',
                           help='Save the unused buildset and config files.',
                           type=str,
                           default=None)
        argsp.add_argument(
            '--catalog',
            help='Save the URLs of downloads as a JSON catalog.',
            type=str,
            default=None)
        argsp.add_argument('bsets', nargs='*', help='Build sets.')

        argopts = argsp.parse_args(args[1:])

        simhost.load_log(argopts.log)
        log.notice('RTEMS Source Builder - Get Sources, %s' %
                   (version.string()))
        log.tracing = argopts.trace

        if argopts.no_download:
            download_opt = '--no-download'
        else:
            download_opt = '--with-download'

        opts = simhost.load_options(args,
                                    argopts,
                                    extras=['--dry-run', download_opt])
        configs = build.get_configs(opts)

        stop_on_error = not argopts.keep_going

        if argopts.list_hosts:
            simhost.list_hosts()
        elif argopts.list_bsets:
            simhost.list_bset_files(opts, configs)
        elif argopts.list_root_bsets:
            simhost.list_root_bset_files(opts, configs)
        else:
            if argopts.clean:
                if argopts.download_dir is None:
                    raise error.general(
                        'cleaning of the default download directories is not supported'
                    )
                if path.exists(argopts.download_dir):
                    log.notice('Cleaning source directory: %s' %
                               (argopts.download_dir))
                    path.removeall(argopts.download_dir)
            if len(argopts.bsets) == 0:
                bsets = simhost.get_root_bset_files(opts, configs)
            else:
                bsets = argopts.bsets
            deps = copy.copy(simhost.strip_common_prefix(bsets))
            sources = {'sources': [], 'patches': [], 'hashes': []}
            for bset in bsets:
                b = None
                try:
                    for host in simhost.profiles:
                        get_sources_error = True
                        b = simhost.buildset(bset, configs, opts)
                        get_sources_error = False
                        b.build(host)
                        deps += b.deps()
                        sources['sources'] += b._sources
                        sources['patches'] += b._patches
                        sources['hashes'] += b._hashes
                        del b
                except error.general as gerr:
                    if stop_on_error:
                        raise
                    log.stderr(str(gerr))
                    log.stderr('Build FAILED')
                b = None
            deps = sorted(list(set(deps)))
            if argopts.used:
                with open(argopts.used, 'w') as o:
                    o.write(os.linesep.join(deps))
            if argopts.unused:
                cfgs_bsets = \
                    [cb for cb in simhost.get_config_bset_files(opts, configs) if not cb in deps]
                with open(argopts.unused, 'w') as o:
                    o.write(os.linesep.join(cfgs_bsets))
            if argopts.catalog is not None:
                sources['sources'] = process_sources(sources['sources'])
                sources['patches'] = process_sources(sources['patches'])
                sources['hashes'] = process_hashes(sources['hashes'])
                print('Catalog has',
                      len(sources['sources']), 'source packages,',
                      len(sources['patches']), 'patches and',
                      len(sources['hashes']), 'hashes')
                with open(argopts.catalog, 'w') as f:
                    f.write(json.dumps(sources, indent=2))
    except error.general as gerr:
        if get_sources_error:
            log.stderr(str(gerr))
        log.stderr('Build FAILED')
        ec = 1
    except error.internal as ierr:
        if get_sources_error:
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
