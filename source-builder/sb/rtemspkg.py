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
rtems_pkg_cfgs = [
    {
        'label': 'RTEMS Tools',
        'config': 'tools/rtems-tools-%{rtems_version}.cfg',
        'version': 'rtems_tools_version',
        'repo':
        'git://gitlab.rtems.org/rtems/tools/rtems-tools.git?protocol=https',
        'repo-name': 'rtems-tools.git',
        'branch': 'main',
        'snapshot':
        'https://gitlab.rtems.org/rtems/tools/rtems-tools/-/archive/%{rtems_tools_version}/rtems-tools-%{rtems_tools_version}.tar.bz2',
        'package': 'rtems-tools-%{rtems_tools_version}.tar.bz2'
    },
    {
        'label': 'RTEMS Kernel',
        'config': 'tools/rtems-kernel-%{rtems_version}.cfg',
        'version': 'rtems_kernel_version',
        'repo': 'git://gitlab.rtems.org/rtems/rtos/rtems.git?protocol=https',
        'repo-name': 'rtems.git',
        'branch': 'main',
        'snapshot':
        'https://gitlab.rtems.org/rtems/rtos/rtems/-/archive/%{rtems_kernel_version}/rtems-%{rtems_kernel_version}.tar.bz2',
        'package': 'rtems-kernel-%{rtems_kernel_version}.tar.bz2'
    },
    {
        'label': 'RTEMS LibBSD',
        'config': 'tools/rtems-libbsd-%{rtems_version}.cfg',
        'version': 'rtems_libbsd_version',
        'repo':
        'git://gitlab.rtems.org/rtems/pkg/rtems-libbsd.git?protocol=https',
        'repo-name': 'rtems-libbsd.git',
        'branch': '6-freebsd-12',
        'snapshot':
        'https://gitlab.rtems.org/rtems/pkg/rtems-libbsd/-/archive/%{rtems_libbsd_version}/rtems-libbsd-%{rtems_libbsd_version}.tar.%{rtems_libbsd_ext}',
        'package':
        'rtems-libbsd-%{rtems_libbsd_version}.tar.%{rtems_libbsd_ext}',
        'submodules': {
            'rtems_waf': {
                'label': 'RTEMS Waf',
                'config': 'tools/rtems-libbsd-%{rtems_version}.cfg',
                'version': 'rtems_waf_version',
                'repo':
                'git://gitlab.rtems.org/rtems/tools/rtems_waf.git?protocol=https',
                'repo-name': 'rtems_waf.git',
                'branch': 'main',
                'snapshot':
                'https://gitlab.rtems.org/rtems/tools/rtems_waf/-/archive/%{rtems_waf_version}/rtems_waf-%{rtems_waf_version}.tar.%{rtems_waf_ext}',
                'package':
                'rtems_waf-%{rtems_waf_version}.tar.%{rtems_waf_ext}'
            }
        }
    },
    {
        'label': 'RTEMS Net Legacy',
        'config': 'tools/rtems-net-legacy-%{rtems_version}.cfg',
        'version': 'rtems_net_version',
        'repo':
        'git://gitlab.rtems.org/rtems/pkg/rtems-net-legacy.git?protocol=https',
        'repo-name': 'rtems-net-legacy.git',
        'branch': 'main',
        'snapshot':
        'https://gitlab.rtems.org/rtems/pkg/rtems-net-legacy/-/archive/%{rtems_net_version}/rtems-net-legacy-%{rtems_net_version}.tar.%{rtems_net_ext}',
        'package':
        'rtems-net-legacy-%{rtems_net_version}.tar.%{rtems_net_ext}',
        'submodules': {
            'rtems_waf': {
                'label': 'RTEMS Waf',
                'config': 'tools/rtems-net-legacy-%{rtems_version}.cfg',
                'version': 'rtems_waf_version',
                'repo':
                'git://gitlab.rtems.org/rtems/tools/rtems_waf.git?protocol=https',
                'repo-name': 'rtems_waf.git',
                'branch': 'main',
                'snapshot':
                'https://gitlab.rtems.org/rtems/tools/rtems_waf/-/archive/%{rtems_waf_version}/rtems_waf-%{rtems_waf_version}.tar.%{rtems_waf_ext}',
                'package':
                'rtems_waf-%{rtems_waf_version}.tar.%{rtems_waf_ext}'
            }
        }
    },
    {
        'label': 'RTEMS Net Services',
        'config': 'net/net-services-1.cfg',
        'version': 'rtems_net_services_version',
        'repo':
        'git://gitlab.rtems.org/rtems/pkg/rtems-net-services.git?protocol=https',
        'repo-name': 'rtems-net-services.git',
        'branch': 'main',
        'snapshot':
        'https://gitlab.rtems.org/rtems/pkg/rtems-net-services/-/archive/%{rtems_net_services_version}/rtems-net-services-%{rtems_net_services_version}.tar.%{rtems_net_services_ext}',
        'package':
        'rtems-net-services-%{rtems_net_services_version}.tar.%{rtems_net_services_ext}',
        'submodules': {
            'rtems_waf': {
                'label': 'RTEMS Waf',
                'config': 'net/net-services-1.cfg',
                'version': 'rtems_waf_version',
                'repo':
                'git://gitlab.rtems.org/rtems/tools/rtems_waf.git?protocol=https',
                'repo-name': 'rtems_waf.git',
                'branch': 'main',
                'snapshot':
                'https://gitlab.rtems.org/rtems/tools/rtems_waf/-/archive/%{rtems_waf_version}/rtems_waf-%{rtems_waf_version}.tar.%{rtems_waf_ext}',
                'package':
                'rtems_waf-%{rtems_waf_version}.tar.%{rtems_waf_ext}'
            }
        }
    },
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


def process_package(config, opts, argopts):
    bopts = copy.copy(opts)
    bmacros = copy.copy(opts.defaults)
    b = build.build(config['config'], False, bopts, bmacros)
    source_dir = b.macros.expand('%{_sourcedir}')
    config_hash = b.macros.expand('%{' + config['version'] + '}')
    if len(config_hash) == 0:
        raise error.general(config['label'] + ': cannot find version macro: ' +
                            config['version'])
    repo_path = path.join(source_dir, config['repo-name'])
    download.get_file(
        config['repo'] + '?fetch?checkout=' + config['branch'] + '?pull',
        repo_path, bopts, b)
    repo = git.repo(repo_path)
    if repo.dirty():
        raise error.general(config['label'] + ': repo is dirty')
    repo_hash = repo.head()
    if config_hash != repo_hash:
        update = True
        update_str = 'UPDATE'
    else:
        update = False
        update_str = 'matching'
    print(config['label'] + ': ' + update_str + ' config:' + config_hash +
          ' repo:' + repo_hash)
    b.macros[config['version']] = repo_hash
    tarball = b.macros.expand(config['package'])
    b.macros.set_write_map('hashes')
    b.macros[tarball] = 'NO-HASH NO-HASH'
    b.macros.unset_write_map()
    tarball_path = path.join(source_dir, b.macros.expand(config['package']))
    download.get_file(b.macros.expand(config['snapshot']), tarball_path, bopts,
                      b)
    tarball_hash = checksum_sha512_base64(tarball_path)
    if update and not argopts.dry_run:
        config_patch(b.macros, '%{_configdir}', config['config'],
                     config['package'], config['version'], config_hash,
                     repo_hash, tarball_hash)
    repo_submodules = repo.submodules()
    if len(repo_submodules) == 0 and 'submodules' in config:
        raise error.general('package has no submodule and some defined: ' +
                            config['label'])
    if len(repo_submodules) != 0:
        if 'submodules' not in config:
            raise error.general('package has submodules, none defined: ' +
                                config['label'])
        for submodule in config['submodules']:
            if submodule not in repo_submodules:
                raise error.general('untraced submodule ' + submodule +
                                    ' in ' + config['label'])
            repo_hash = repo_submodules[submodule]
            config_submodule = config['submodules'][submodule]
            config_hash = b.macros.expand('%{' + config_submodule['version'] +
                                          '}')
            if len(config_hash) == 0:
                raise error.general(config_submodule['label'] +
                                    ': cannot find version macro: ' +
                                    config_submodule['version'])
            if config_hash != repo_hash:
                update = True
                update_str = 'UPDATE'
            else:
                update = False
                update_str = 'matching'
            print(' Submodule: ' + config_submodule['label'] + ': ' +
                  update_str + ' config:' + config_hash + ' repo:' + repo_hash)
            if update and not argopts.dry_run:
                b.macros[config_submodule['version']] = repo_hash
                tarball = b.macros.expand(config_submodule['package'])
                b.macros.set_write_map('hashes')
                b.macros[tarball] = 'NO-HASH NO-HASH'
                b.macros.unset_write_map()
                tarball_path = path.join(
                    source_dir, b.macros.expand(config_submodule['package']))
                download.get_file(
                    b.macros.expand(config_submodule['snapshot']),
                    tarball_path, bopts, b)
                tarball_hash = checksum_sha512_base64(tarball_path)
                config_patch(b.macros, '%{_configdir}',
                             config_submodule['config'],
                             config_submodule['package'],
                             config_submodule['version'], config_hash,
                             repo_hash, tarball_hash)
    del repo
    del b


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
            try:
                process_package(cfg, opts, argopts)
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
