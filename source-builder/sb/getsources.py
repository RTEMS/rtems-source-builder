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
import os
import sys

try:
    from . import build
    from . import error
    from . import log
    from . import simhost
    from . import version
except KeyboardInterrupt:
    print('abort: user terminated', file = sys.stderr)
    sys.exit(1)
except:
    raise

def run(args = sys.argv):
    ec = 0
    get_sources_error = True
    try:
        #
        # The RSB options support cannot be used because it loads the defaults
        # for the host which we cannot do here.
        #
        description  = 'RTEMS Get Sources downloads all the source a build set '
        description += 'references for all hosts.'

        argsp = argparse.ArgumentParser(prog = 'rtems-get-sources',
                                        description = description)
        argsp.add_argument('--rtems-version', help = 'Set the RTEMS version.',
                           type = str,
                           default = version.version())
        argsp.add_argument('--list-hosts', help = 'List the hosts.',
                           action = 'store_true')
        argsp.add_argument('--list-bsets', help = 'List the hosts.',
                           action = 'store_true')
        argsp.add_argument('--download-dir', help = 'Download directory.',
                           type = str)
        argsp.add_argument('--clean', help = 'Clean the download directory.',
                           action = 'store_true')
        argsp.add_argument('--tar', help = 'Create a tarball of all the source.',
                           action = 'store_true')
        argsp.add_argument('--log', help = 'Log file.',
                           type = str,
                           default = simhost.log_default('getsource'))
        argsp.add_argument('--trace', help = 'Enable trace logging for debugging.',
                           action = 'store_true')
        argsp.add_argument('bsets', nargs='*', help = 'Build sets.')

        argopts = argsp.parse_args(args[1:])

        simhost.load_log(argopts.log)
        log.notice('RTEMS Source Builder - Get Sources, %s' % (version.string()))
        log.tracing = argopts.trace

        opts = simhost.load_options(args, argopts, extras = ['--with-download'])
        configs = build.get_configs(opts)

        if argopts.list_hosts:
            simhost.list_hosts()
        elif argopts.list_bsets:
            simhost.list_bset_files(opts, configs)
        else:
            if argopts.clean:
                if argopts.download_dir is None:
                    raise error.general('cleaning of the default download directories is not supported')
                if path.exists(argopts.download_dir):
                    log.notice('Cleaning source directory: %s' % (argopts.download_dir))
                    path.removeall(argopts.download_dir)
            all_bsets = simhost.get_bset_files(configs)
            if len(argopts.bsets) == 0:
                bsets = all_bsets
            else:
                bsets = argopts.bsets
            for bset in bsets:
                b = None
                try:
                    for host in simhost.profiles:
                        get_sources_error = True
                        b = simhost.buildset(bset, configs, opts)
                        get_sources_error = False
                        b.build(host)
                        del b
                except error.general as gerr:
                    log.stderr(str(gerr))
                    log.stderr('Build FAILED')
                b = None
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
