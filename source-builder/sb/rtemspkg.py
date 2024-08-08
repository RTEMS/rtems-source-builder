#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2024 Chris Johns (chrisj@rtems.org)
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
import base64
import copy
import datetime
import hashlib
import os
import sys

try:
    from . import build
    from . import download
    from . import error
    from . import git
    from . import log
    from . import path
    from . import simhost
    from . import version
except KeyboardInterrupt:
    print('abort: user terminated', file=sys.stderr)
    sys.exit(1)
except:
    raise

#
# RTEMS Packages we maintian a git hash of in the RSB
#
rpc_label = 0
rpc_config = 1
rpc_version = 2
rpc_repo = 3
rpc_repo_name = 4
rpc_branch = 5
rpc_snapshot = 6
rpc_package = 7
rtems_pkg_cfgs = [
    [
        'RTEMS Tools', 'tools/rtems-tools-%{rtems_version}.cfg',
        'rtems_tools_version',
        'git://gitlab.rtems.org/rtems/tools/rtems-tools.git?protocol=https',
        'rtems-tools.git', 'main',
        'https://gitlab.rtems.org/rtems/tools/rtems-tools/-/archive/%{rtems_tools_version}/rtems-tools-%{rtems_tools_version}.tar.bz2',
        'rtems-tools-%{rtems_tools_version}.tar.bz2'
    ],
    [
        'RTEMS Kernel', 'tools/rtems-kernel-%{rtems_version}.cfg',
        'rtems_kernel_version',
        'git://gitlab.rtems.org/rtems/rtos/rtems.git?protocol=https',
        'rtems.git', 'main',
        'https://gitlab.rtems.org/rtems/rtos/rtems/-/archive/%{rtems_kernel_version}/rtems-%{rtems_kernel_version}.tar.bz2',
        'rtems-kernel-%{rtems_kernel_version}.tar.bz2'
    ],
    [
        'RTEMS LibBSD', 'tools/rtems-libbsd-%{rtems_version}.cfg',
        'rtems_libbsd_version',
        'git://gitlab.rtems.org/rtems/pkg/rtems-libbsd.git?protocol=https',
        'rtems-libbsd.git', '6-freebsd-12',
        'https://gitlab.rtems.org/rtems/pkg/rtems-libbsd/-/archive/%{rtems_libbsd_version}/rtems-libbsd-%{rtems_libbsd_version}.tar.%{rtems_libbsd_ext}',
        'rtems-libbsd-%{rtems_libbsd_version}.tar.%{rtems_libbsd_ext}'
    ],
    [
        'RTEMS Net Legacy', 'tools/rtems-net-legacy-%{rtems_version}.cfg',
        'rtems_net_version',
        'git://gitlab.rtems.org/rtems/pkg/rtems-net-legacy.git?protocol=https',
        'rtems-net-legacy.git', 'main',
        'https://gitlab.rtems.org/rtems/pkg/rtems-net-legacy/-/archive/%{rtems_net_version}/rtems-net-legacy-%{rtems_net_version}.tar.%{rtems_net_ext}',
        'rtems-net-legacy-%{rtems_net_version}.tar.%{rtems_net_ext}'
    ],
    [
        'RTEMS Net Services', 'net/net-services-1.cfg',
        'rtems_net_services_version',
        'git://gitlab.rtems.org/rtems/pkg/rtems-net-services.git?protocol=https',
        'rtems-net-services.git', 'main',
        'https://gitlab.rtems.org/rtems/pkg/rtems-net-services/-/archive/%{rtems_net_services_version}/rtems-net-services-%{rtems_net_services_version}.tar.%{rtems_net_services_ext}',
        'rtems-net-services-%{rtems_net_services_version}.tar.%{rtems_net_services_ext}'
    ],
]


def clean_line(line):
    line = line[0:-1]
    b = line.find('#')
    if b >= 0:
        line = line[1:b] + ('\\' if line[-1] == '\\' else '')
    return line.strip()


def clean_and_pack(line, last_line):
    leading_ws = ' ' if len(line) > 0 and line[0].isspace() else ''
    line = clean_line(line)
    if len(last_line) > 0:
        line = last_line + leading_ws + line
    return line


def config_patch(macros, mconfigdir, pkg_config, pkg_package, version_label,
                 config_hash, repo_hash, checksum):
    macros[version_label] = config_hash
    configdir = macros.expand(mconfigdir)
    config = macros.expand(pkg_config)
    package = macros.expand(pkg_package)
    for cd in configdir.split(':'):
        cf = path.join(cd, config)
        if path.exists(cf):
            try:
                with open(cf) as f:
                    lines = f.readlines()
            except IOError as err:
                raise error.general('config: %s: read error: %s' %
                                    (config, str(err)))
            new_config = []
            new_lines = []
            last_line = ''
            for line in lines:
                new_lines += [line]
                line = clean_and_pack(line, last_line)
                if len(line) > 0:
                    if line[-1] == '\\':
                        last_line = line[:-1]
                        continue
                    last_line = ''
                    try:
                        eline = macros.expand(line)
                    except:
                        eline = line
                    if (version_label in line and not 'rsb_version' in line) or \
                       package in eline:
                        if line.startswith('%define ' + version_label):
                            new_lines = [
                                '%define ' + version_label + ' ' + repo_hash +
                                os.linesep
                            ]
                        elif line.startswith('%hash '):
                            ls = line.split()
                            if len(ls) != 4:
                                raise error.general('invalid %hash: ' + line)
                            new_lines = [
                                ' '.join(ls[0:3]) + ' \\' + os.linesep,
                                '              ' + checksum + os.linesep
                            ]
                new_config += new_lines
                new_lines = []
            try:
                with open(cf, 'w') as f:
                    f.writelines(new_config)
            except IOError as err:
                raise error.general('config: %s: write error: %s' %
                                    (config, str(err)))
            return
    raise error.general('could not find: ' + config)


def checksum_sha512_base64(tarball):
    hasher = hashlib.new('sha512')
    try:
        with open(path.host(tarball), 'rb') as f:
            hasher.update(f.read())
    except IOError as err:
        log.notice('hash: %s: read error: %s' % (file_, str(err)))
    except:
        raise
        raise error.general('cannot hash the tar file')
    hash_hex = hasher.hexdigest()
    hash_base64 = base64.b64encode(hasher.digest()).decode('utf-8')
    return hash_base64


def run(args=sys.argv):
    ec = 0
    output = []
    try:
        #
        # The RSB options support cannot be used because it loads the defaults
        # for the host which we cannot do here.
        #
        description = 'RTEMS Track Dependencies a build set has for all hosts.'

        argsp = argparse.ArgumentParser(prog='sb-rtems-pkg',
                                        description=description)
        argsp.add_argument('--rtems-version',
                           help='Set the RTEMS version.',
                           type=str,
                           default=version.version())
        argsp.add_argument('--log',
                           help='Log file.',
                           type=str,
                           default=simhost.log_default('rtems-pkg'))
        argsp.add_argument('--trace',
                           help='Enable trace logging for debugging.',
                           action='store_true')
        argsp.add_argument('--dry-run',
                           help='Dry run, do not update the configurations',
                           action='store_true')
        argsp.add_argument('bsets', nargs='*', help='Build sets.')

        argopts = argsp.parse_args(args[1:])

        simhost.load_log(argopts.log)
        log.notice('RTEMS Source Builder - RTEMS Package Update, %s' %
                   (version.string()))
        log.tracing = argopts.trace

        opts = simhost.load_options(args, argopts, extras=['--with-download'])
        opts.defaults['_rsb_getting_source'] = '1'
        opts.defaults[
            'rtems_waf_build_root_suffix'] = '%{waf_build_root_suffix}'
        opts.defaults['rtems_version'] = argopts.rtems_version

        for cfg in rtems_pkg_cfgs:
            b = None
            try:
                bopts = copy.copy(opts)
                bmacros = copy.copy(opts.defaults)
                b = build.build(cfg[rpc_config], False, bopts, bmacros)
                git_hash_key = b.macros.find(cfg[rpc_version])
                if len(git_hash_key) == 0:
                    raise error.general(cfg[rpc_label] +
                                        ': cannot find version macro')
                source_dir = b.macros.expand('%{_sourcedir}')
                config_hash = b.macros.expand('%{' + cfg[rpc_version] + '}')
                repo_path = path.join(source_dir, cfg[rpc_repo_name])
                download.get_file(
                    cfg[rpc_repo] + '?fetch?checkout=' + cfg[rpc_branch] + '?pull',
                    repo_path, bopts, b)
                repo = git.repo(repo_path)
                if repo.dirty():
                    raise error.general(cfg[rpc_label] +
                                        ': repo is dirty')
                repo_hash = repo.head()
                if config_hash != repo_hash:
                    update = True
                    update_str = 'UPDATE'
                else:
                    update = False
                    update_str = 'matching'
                print(cfg[rpc_label] + ': ' + update_str + ' config:' +
                      config_hash + ' repo:' + repo_hash)
                b.macros[cfg[rpc_version]] = repo_hash
                tarball = b.macros.expand(cfg[rpc_package])
                b.macros.set_write_map('hashes')
                b.macros[tarball] = 'NO-HASH NO-HASH'
                b.macros.unset_write_map()
                tarball_path = path.join(source_dir,
                                         b.macros.expand(cfg[rpc_package]))
                download.get_file(b.macros.expand(cfg[rpc_snapshot]),
                                  tarball_path, bopts, b)
                tarball_hash = checksum_sha512_base64(tarball_path)
                if update and not argopts.dry_run:
                    config_patch(b.macros, '%{_configdir}', cfg[rpc_config],
                                 cfg[rpc_package], cfg[rpc_version],
                                 config_hash, repo_hash, tarball_hash)
                del b
            except error.general as gerr:
                log.stderr(str(gerr))
                log.stderr('Configuration load FAILED')
                b = None
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
