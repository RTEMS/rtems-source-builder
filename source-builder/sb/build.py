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
# This code builds a package given a config file. It only builds to be
# installed not to be package unless you run a packager around this.
#

from __future__ import print_function

import copy
import getopt
import glob
import os
import shutil
import stat
import sys

try:
    from . import check
    from . import config
    from . import download
    from . import error
    from . import ereport
    from . import execute
    from . import log
    from . import options
    from . import path
    from . import sources
    from . import version
except KeyboardInterrupt:
    print('abort: user terminated')
    sys.exit(1)
except:
    raise


def humanize_number(num, suffix):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%5.3f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.3f%s%s" % (size, 'Y', suffix)


def short_name(name):
    #
    # If on Windows use short names to keep the build paths as short as possible.
    #
    if options.host_windows:
        buildname = ''
        add = True
        for n in name.split('-'):
            if n:
                buildname += n[0]
        return buildname
    else:
        return name


class script:
    """Create and manage a shell script."""

    def __init__(self):
        self.reset()

    def __str__(self):
        i = 0
        text = []
        for l in self.body:
            i += 1
            text += ['script:%3d: %s' % (self.lc + i, l)]
        return os.linesep.join(text)

    def reset(self):
        self.body = []
        self.lc = 0

    def append(self, text):
        is_str = False
        if type(text) is str:
            is_str = True
        try:
            if type(text) is unicode:
                is_str = True
        except:
            pass
        if is_str:
            text = text.splitlines()
        if not log.quiet:
            i = 0
            for l in text:
                i += 1
                log.output('script:%3d: %s' % (self.lc + i, l))
        self.lc += len(text)
        self.body.extend(text)

    def write(self, name, check_for_errors=False):
        s = None
        try:
            s = open(path.host(name), 'w')
            s.write(os.linesep.join(self.body))
            s.close()
            os.chmod(path.host(name), stat.S_IRWXU | \
                         stat.S_IRGRP | stat.S_IXGRP | \
                         stat.S_IROTH | stat.S_IXOTH)
        except IOError as err:
            raise error.general('creating script: ' + name)
        except:
            if s is not None:
                s.close()
            raise
        if s is not None:
            s.close()


class build:
    """Build a package given a config file."""

    def _generate_report_(self, header, footer=None):
        ereport.generate('rsb-report-%s.txt' % self.macros['name'], self.opts,
                         header, footer)

    def __init__(self, name, create_tar_files, opts, macros=None):
        try:
            self.opts = opts
            self.init_name = name
            self.init_macros = macros
            self.config = None
            self.create_tar_files = create_tar_files
            log.notice('config: ' + name)
            self.set_macros(macros)
            self.config = config.file(name, opts, self.macros)
            self.script_build = script()
            self.script_clean = script()
            self.macros['buildname'] = short_name(self.macros['name'])
        except error.general as gerr:
            log.notice(str(gerr))
            log.stderr('Build FAILED')
            raise
        except error.internal as ierr:
            log.notice(str(ierr))
            log.stderr('Internal Build FAILED')
            raise
        except:
            raise

    def copy_init_macros(self):
        return copy.copy(self.init_macros)

    def copy_macros(self):
        return copy.copy(self.macros)

    def set_macros(self, macros):
        if macros is None:
            self.macros = copy.copy(self.opts.defaults)
        else:
            self.macros = copy.copy(macros)
        if self.config:
            self.config.set_macros(self.macros)

    def rmdir(self, rmpath):
        log.output('removing: %s' % (path.host(rmpath)))
        if not self.opts.dry_run():
            if path.exists(rmpath):
                path.removeall(rmpath)

    def mkdir(self, mkpath):
        log.output('making dir: %s' % (path.host(mkpath)))
        if not self.opts.dry_run():
            path.mkdir(mkpath)

    def canadian_cross(self):
        _host = self.config.expand('%{_host}')
        _build = self.config.expand('%{_build}')
        _target = self.config.expand('%{_target}')
        _allowed = self.config.defined('%{allow_cxc}')
        if len(_host) and len(_build) and (_target) and \
           _allowed and _host != _build and _host != _target:
            return True
        return False

    def installable(self):
        _host = self.config.expand('%{_host}')
        _build = self.config.expand('%{_build}')
        _canadian_cross = self.canadian_cross()
        if self.macros.get('_disable_installing') and \
           self.config.expand('%{_disable_installing}') == 'yes':
            _disable_installing = True
        else:
            _disable_installing = False
        _no_install = self.opts.no_install()
        log.trace('_build: installable: host=%s build=%s ' \
                  'no-install=%r Cxc=%r disable_installing=%r disabled=%r' % \
                  (_host, _build, _no_install, _canadian_cross, _disable_installing, \
                   self.disabled()))
        return len(_host) and len(_build) and \
            not self.disabled() and \
            not _disable_installing and \
            not _canadian_cross

    def source(self, name, strip_components, download_only):
        #
        # Return the list of sources. Merge in any macro defined sources as
        # these may be overridden by user loaded macros.
        #
        _map = 'source-%s' % (name)
        src_keys = [s for s in self.macros.map_keys(_map) if s != 'setup']
        if len(src_keys) == 0:
            raise error.general('no source set: %s (%s)' % (name, _map))
        srcs = []
        for s in src_keys:
            sm = self.macros.get(s, globals=False, maps=_map)
            if sm is None:
                raise error.internal('source macro not found: %s in %s (%s)' % \
                                         (s, name, _map))
            opts = []
            url = []
            for sp in sm[2].split():
                if len(url) == 0 and sp[0] == '-':
                    opts += [sp]
                else:
                    url += [sp]
            if len(url) == 0:
                raise error.general('source URL not found: %s' %
                                    (' '.join(args)))
            #
            # Look for --rsb-file as an option we use as a local file name.
            # This can be used if a URL has no reasonable file name the
            # download URL parser can figure out.
            #
            file_override = None
            if len(opts) > 0:
                for o in opts:
                    if o.startswith('--rsb-file'):
                        os_ = o.split('=')
                        if len(os_) != 2:
                            raise error.general('invalid --rsb-file option: %s' % \
                                                (' '.join(args)))
                        if os_[0] != '--rsb-file':
                            raise error.general('invalid --rsb-file option: %s' % \
                                                (' '.join(args)))
                        file_override = os_[1]
                opts = [o for o in opts if not o.startswith('--rsb-')]
            url = self.config.expand(' '.join(url))
            src = download.parse_url(url, '_sourcedir', self.config, self.opts,
                                     file_override)
            download.get_file(src['url'], src['local'], self.opts, self.config)
            if not download_only:
                if self.opts.trace():
                    tar_extract_key = '__tar_extract_trace'
                else:
                    tar_extract_key = '__tar_extract'
                if strip_components > 0:
                    tar_extract = '%{' + tar_extract_key + '} --strip-components %d' % \
                        (strip_components)
                else:
                    tar_extract = '%{' + tar_extract_key + '}'
                if 'symlink' in src:
                    sname = name.replace('-', '_')
                    src['script'] = '%%{__ln_s} %s ${source_dir_%s}' % \
                        (src['symlink'], sname)
                elif 'compressed' in src:
                    #
                    # Zip files unpack as well so do not use tar.
                    #
                    src['script'] = '%s %s' % (src['compressed'], src['local'])
                    if src['compressed-type'] != 'zip':
                        src['script'] += ' | %s -f -' % (tar_extract)
                else:
                    src['script'] = '%s -f %s' % (tar_extract, src['local'])
                srcs += [src]
        return srcs

    def source_setup(self, package, args):
        log.output('source setup: %s: %s' % (package.name(), ' '.join(args)))
        setup_name = args[1]
        args = args[1:]
        try:
            opts, args = getopt.getopt(args[1:], 'qDcn:bas:gE')
        except getopt.GetoptError as ge:
            raise error.general('source setup error: %s' % str(ge))
        quiet = False
        unpack_before_chdir = True
        delete_before_unpack = True
        create_dir = False
        deleted_dir = False
        created_dir = False
        changed_dir = False
        no_errors = False
        strip_components = 0
        opt_name = None
        download_only = False
        for o in opts:
            if o[0] == '-q':
                quiet = True
            elif o[0] == '-D':
                delete_before_unpack = False
            elif o[0] == '-c':
                create_dir = True
            elif o[0] == '-n':
                opt_name = o[1]
            elif o[0] == '-b':
                unpack_before_chdir = True
            elif o[0] == '-a':
                unpack_before_chdir = False
            elif o[0] == '-E':
                no_errors = True
            elif o[0] == '-s':
                if not o[1].isdigit():
                    raise error.general('source setup error: invalid strip count: %s' % \
                                        (o[1]))
                strip_components = int(o[1])
            elif o[0] == '-g':
                download_only = True
        name = None
        for source in self.source(setup_name, strip_components, download_only):
            if name is None:
                if opt_name is None:
                    if source:
                        opt_name = source['name']
                    else:
                        raise error.general('setup source tag not found: %d' % \
                                            (source_tag))
                else:
                    name = opt_name
            if not download_only:
                self.script_build.append(self.config.expand('cd %{_builddir}'))
                if not deleted_dir and delete_before_unpack and name is not None:
                    self.script_build.append(
                        self.config.expand('%{__rm} -rf ' + name))
                    deleted_dir = True
                if not created_dir and create_dir and name is not None:
                    self.script_build.append(
                        self.config.expand('%{__mkdir_p} ' + name))
                    created_dir = True
                if not changed_dir and (not unpack_before_chdir or create_dir) and \
                   name is not None:
                    self.script_build.append(self.config.expand('cd ' + name))
                    changed_dir = True
                #
                # On Windows tar can fail on links if the link appears in the
                # tar file before the target of the link exists. We can assume the
                # tar file is correct, that is all files and links are valid,
                # so on error redo the untar a second time.
                #
                if options.host_windows or no_errors:
                    self.script_build.append('set +e')
                self.script_build.append(self.config.expand(source['script']))
                if options.host_windows or not no_errors:
                    self.script_build.append('tar_exit=$?')
                if options.host_windows or no_errors:
                    self.script_build.append('set -e')
                if options.host_windows:
                    if no_errors:
                        self.script_build.append(' set +e')
                        self.script_build.append(
                            ' ' + self.config.expand(source['script']))
                        self.script_build.append(' set -e')
                    else:
                        self.script_build.append(
                            'if test $tar_exit != 0; then')
                        self.script_build.append(
                            ' ' + self.config.expand(source['script']))
                        self.script_build.append('fi')
        if not changed_dir and (unpack_before_chdir and not create_dir) and \
           name is not None and not download_only:
            self.script_build.append(self.config.expand('cd ' + name))
            changed_dir = True
        self.script_build.append(self.config.expand('%{__setup_post}'))

    def patch_setup(self, package, args):
        name = args[1]
        args = args[2:]
        _map = 'patch-%s' % (name)
        default_opts = ' '.join(args)
        patch_keys = [p for p in self.macros.map_keys(_map) if p != 'setup']
        patches = []
        for p in patch_keys:
            pm = self.macros.get(p, globals=False, maps=_map)
            if pm is None:
                raise error.internal('patch macro not found: %s in %s (%s)' % \
                                         (p, name, _map))
            opts = []
            url = []
            for pp in pm[2].split():
                if len(url) == 0 and pp[0] == '-':
                    opts += [pp]
                else:
                    url += [pp]
            if len(url) == 0:
                raise error.general('patch URL not found: %s' %
                                    (' '.join(opts)))
            #
            # Look for --rsb-file as an option we use as a local file name.
            # This can be used if a URL has no reasonable file name the
            # download URL parser can figure out.
            #
            file_override = None
            if len(opts) > 0:
                for o in opts:
                    if o.startswith('--rsb-file'):
                        os_ = o.split('=')
                        if len(os_) != 2:
                            raise error.general('invalid --rsb-file option: %s' % \
                                                (' '.join(opts)))
                        if os_[0] != '--rsb-file':
                            raise error.general('invalid --rsb-file option: %s' % \
                                                (' '.join(opts)))
                        file_override = os_[1]
                opts = [o for o in opts if not o.startswith('--rsb-')]
            if len(opts) == 0:
                opts = default_opts
            else:
                opts = ' '.join(opts)
            opts = self.config.expand(opts)
            url = self.config.expand(' '.join(url))
            #
            # Parse the URL first in the source builder's patch directory.
            #
            patch = download.parse_url(url, '_patchdir', self.config,
                                       self.opts, file_override)
            #
            # Download the patch
            #
            download.get_file(patch['url'], patch['local'], self.opts,
                              self.config)
            if 'compressed' in patch:
                patch['script'] = patch['compressed'] + ' ' + patch['local']
            else:
                patch['script'] = '%{__cat} ' + patch['local']
            patch['script'] += ' | %%{__patch} %s' % (opts)
            self.script_build.append(self.config.expand(patch['script']))

    def run(self, command, shell_opts='', cwd=None):
        e = execute.capture_execution(log=log.default, dump=self.opts.quiet())
        cmd = self.config.expand('%{___build_shell} -ex ' + shell_opts + ' ' +
                                 command)
        log.output('run: ' + cmd)
        exit_code, proc, output = e.shell(cmd, cwd=path.host(cwd))
        if exit_code != 0:
            log.output('shell cmd failed: %s' % (cmd))
            raise error.general('building %s' % (self.macros['buildname']))

    def builddir(self):
        builddir = self.config.abspath('_builddir')
        if not self.opts.dry_run():
            self.rmdir(builddir)
            self.mkdir(builddir)

    def prep(self, package):
        self.script_build.append('echo "==> %prep:"')
        _prep = package.prep()
        if _prep:
            for l in _prep:
                args = l.split()
                if len(args):

                    def err(msg):
                        raise error.general('%s: %s' % (package, msg))

                    if args[0] == '%setup':
                        if len(args) == 1:
                            raise error.general('invalid %%setup directive: %s' % \
                                                (' '.join(args)))
                        if args[1] == 'source':
                            self.source_setup(package, args[1:])
                        elif args[1] == 'patch':
                            self.patch_setup(package, args[1:])
                    elif args[0] in ['%patch', '%source']:
                        sources.process(args[0][1:], args[1:], self.macros,
                                        err)
                    elif args[0] == '%hash':
                        sources.hash(args[1:], self.macros, err)
                        self.hash(package, args)
                    else:
                        self.script_build.append(' '.join(args))

    def build(self, package):
        self.script_build.append(
            'echo "==> clean %{buildroot}: ${SB_BUILD_ROOT}"')
        self.script_build.append('%s ${SB_BUILD_ROOT}' %
                                 (self.config.expand('%{__rmdir}')))
        self.script_build.append('%s ${SB_BUILD_ROOT}' %
                                 (self.config.expand('%{__mkdir_p}')))
        self.script_build.append('echo "==> %build:"')
        _build = package.build()
        if _build:
            for l in _build:
                self.script_build.append(l)

    def install(self, package):
        self.script_build.append('echo "==> %install:"')
        _install = package.install()
        if _install:
            for l in _install:
                args = l.split()
                self.script_build.append(' '.join(args))

    def files(self, package):
        if self.create_tar_files \
           and not self.macros.get('%{_disable_packaging'):
            self.script_build.append('echo "==> %files:"')
            inpath = path.abspath(self.config.expand('%{buildroot}'))
            tardir = path.abspath(self.config.expand('%{_tardir}'))
            self.script_build.append(
                self.config.expand('if test -d %s; then' % (inpath)))
            self.script_build.append(
                self.config.expand('  %%{__mkdir_p} %s' % tardir))
            self.script_build.append(self.config.expand('  cd ' + inpath))
            tar = path.join(tardir, package.long_name() + '.tar.bz2')
            cmd = self.config.expand('  %{__tar} -cf - . ' +
                                     '| %{__bzip2} > ' + tar)
            self.script_build.append(cmd)
            self.script_build.append(self.config.expand('  cd %{_builddir}'))
            self.script_build.append('fi')

    def clean(self, package):
        self.script_clean.reset()
        self.script_clean.append(self.config.expand('%{___build_template}'))
        self.script_clean.append('echo "=> ' + package.name() + ': CLEAN"')
        self.script_clean.append('echo "==> %clean:"')
        _clean = package.clean()
        if _clean is not None:
            for l in _clean:
                args = l.split()
                self.script_clean.append(' '.join(args))

    def sizes(self, package):

        def _sizes(package, what, path):
            package.set_size(what, path)
            s = humanize_number(package.get_size(what), 'B')
            log.trace('size: %s (%s): %s (%d)' %
                      (what, path, s, package.get_size(what)))
            return s

        s = {}
        for p in [('build', '%{_builddir}'), ('build', '%{buildroot}'),
                  ('installed', '%{buildroot}')]:
            hs = _sizes(package, p[0], self.config.expand(p[1]))
            s[p[0]] = hs
        log.notice('sizes: %s: %s (installed: %s)' %
                   (package.name(), s['build'], s['installed']))

    def build_package(self, package):
        if self.canadian_cross():
            if not self.config.defined('%{allow_cxc}'):
                raise error.general('Canadian Cross is not allowed')
            self.script_build.append('echo "==> Candian-cross build/target:"')
            self.script_build.append('SB_CXC="yes"')
        else:
            self.script_build.append('SB_CXC="no"')
        self.build(package)
        self.install(package)
        self.files(package)
        if not self.opts.no_clean():
            self.clean(package)

    def cleanup(self):
        package = self.main_package()
        if not package.disabled() and not self.opts.no_clean():
            buildroot = self.config.abspath('buildroot')
            builddir = self.config.abspath('_builddir')
            buildcxcdir = self.config.abspath('_buildcxcdir')
            tmproot = self.config.abspath('_tmproot')
            log.trace('cleanup: %s' % (buildroot))
            self.rmdir(buildroot)
            log.trace('cleanup: %s' % (builddir))
            self.rmdir(builddir)
            if self.canadian_cross():
                log.trace('cleanup: %s' % (buildcxcdir))
                self.rmdir(buildcxcdir)
            log.trace('cleanup: %s' % (tmproot))
            self.rmdir(tmproot)

    def main_package(self):
        packages = self.config.packages()
        return packages['main']

    def reload(self):
        self.config.load(self.init_name)

    def make(self):
        package = self.main_package()
        if package.disabled():
            log.notice('package: nothing to build')
        else:
            try:
                name = package.name()
                if self.canadian_cross():
                    cxc_label = '(Cxc) '
                else:
                    cxc_label = ''
                log.notice('package: %s%s' % (cxc_label, name))
                log.trace('---- macro maps %s' % ('-' * 55))
                log.trace('%s' % (str(self.config.macros)))
                log.trace('-' * 70)
                self.script_build.reset()
                self.script_build.append(
                    self.config.expand('%{___build_template}'))
                self.script_build.append('echo "=> ' + name + ': BUILD"')
                self.prep(package)
                self.build_package(package)
                self.builddir()
                build_sn = path.join(self.config.expand('%{_builddir}'),
                                     'do-build')
                clean_sn = path.join(self.config.expand('%{_builddir}'),
                                     'do-clean')
                log.trace('script: ' + build_sn)
                log.trace(str(self.script_build))
                log.trace('script: ' + clean_sn)
                log.trace(str(self.script_clean))
                if not self.opts.dry_run():
                    log.output('write script: ' + build_sn)
                    self.script_build.write(build_sn)
                    log.output('write script: ' + clean_sn)
                    self.script_clean.write(clean_sn)
                    log.notice('building: %s%s' % (cxc_label, name))
                    self.run(build_sn)
                    self.sizes(package)
                    log.notice('cleaning: %s%s' % (cxc_label, name))
                    self.run(clean_sn)
            except error.general as gerr:
                log.notice(str(gerr))
                log.stderr('Build FAILED')
                self._generate_report_('Build: %s' % (gerr))
                raise
            except error.internal as ierr:
                log.notice(str(ierr))
                log.stderr('Internal Build FAILED')
                self._generate_report_('Build: %s' % (ierr))
                raise
            except:
                raise
            if self.opts.dry_run():
                self._generate_report_('Build: dry run (no actual error)',
                                       'Build: dry run (no actual error)')

    def name(self):
        packages = self.config.packages()
        package = packages['main']
        return package.name()

    def disabled(self):
        packages = self.config.packages()
        package = packages['main']
        return package.disabled()

    def get_build_size(self):
        package = self.main_package()
        if package.disabled():
            return 0
        return package.get_size('build')

    def get_installed_size(self):
        package = self.main_package()
        if package.disabled():
            return 0
        return package.get_size('installed')

    def includes(self):
        if self.config:
            return self.config.includes()


def get_configs(opts):

    def _scan(_path, ext):
        configs = []
        for root, dirs, files in os.walk(_path):
            prefix = root[len(_path) + 1:]
            for file in files:
                for e in ext:
                    if file.endswith(e):
                        configs += [path.join(prefix, file)]
        return configs

    configs = {'paths': [], 'files': []}
    paths = opts.defaults.expand('%{_configdir}').split(':')
    root = path.host(os.path.commonprefix(paths))
    configs['root'] = root
    configs['localpaths'] = [lp[len(root):] for lp in paths]
    for cp in paths:
        hcp = path.host(path.abspath(cp))
        configs['paths'] += [hcp]
        hpconfigs = sorted(set(_scan(hcp, ['.cfg', '.bset'])))
        hcplocal = hcp[len(root):]
        configs[hcplocal] = [path.join(hcplocal, c) for c in hpconfigs]
        configs['files'] += hpconfigs
    configs['files'] = sorted(set(configs['files']))
    return configs


def find_config(config, configs):
    config_root, config_ext = path.splitext(config)
    if config_ext not in ['', '.bset', '.cfg']:
        config_root = config
        config_ext = ''
    for c in configs['files']:
        r, e = path.splitext(c)
        if config_root == r:
            if config_ext == '' or config_ext == e:
                return c
    return None


def run(args):
    ec = 0
    try:
        optargs = {'--list-configs': 'List available configurations'}
        opts = options.load(args, optargs)
        log.notice('RTEMS Source Builder, Package Builder, %s' %
                   (version.string()))
        opts.log_info()
        if not check.host_setup(opts):
            if not opts.force():
                raise error.general('host build environment is not set up' +
                                    ' correctly (use --force to proceed)')
            log.notice('warning: forcing build with known host setup problems')
        if opts.get_arg('--list-configs'):
            configs = get_configs(opts)
            for p in configs['paths']:
                print('Examining: %s' % (os.path.relpath(p)))
                for c in configs['files']:
                    if c.endswith('.cfg'):
                        print('    %s' % (c))
        else:
            for config_file in opts.config_files():
                b = build(config_file, True, opts)
                b.make()
                b = None
    except error.general as gerr:
        log.stderr('Build FAILED')
        ec = 1
    except error.internal as ierr:
        log.stderr('Internal Build FAILED')
        ec = 1
    except error.exit as eerr:
        pass
    except KeyboardInterrupt:
        log.notice('abort: user terminated')
        ec = 1
    sys.exit(ec)


if __name__ == "__main__":
    run(sys.argv)
