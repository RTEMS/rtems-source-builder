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
# This code builds a package given a config file. It only builds to be
# installed not to be package unless you run a packager around this.
#

import getopt
import glob
import os
import shutil
import stat
import sys
import urllib2
import urlparse

try:
    import check
    import config
    import download
    import error
    import ereport
    import execute
    import log
    import options
    import path
    import sources
    import version
except KeyboardInterrupt:
    print 'abort: user terminated'
    sys.exit(1)
except:
    print 'error: unknown application load error'
    sys.exit(1)

class script:
    """Create and manage a shell script."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.body = []
        self.lc = 0

    def append(self, text):
        if type(text) is str:
            text = text.splitlines()
        if not log.quiet:
            i = 0
            for l in text:
                i += 1
                log.output('script:%3d: %s' % (self.lc + i, l))
        self.lc += len(text)
        self.body.extend(text)

    def write(self, name, check_for_errors = False):
        s = None
        try:
            s = open(path.host(name), 'w')
            s.write('\n'.join(self.body))
            s.close()
            os.chmod(path.host(name), stat.S_IRWXU | \
                         stat.S_IRGRP | stat.S_IXGRP | \
                         stat.S_IROTH | stat.S_IXOTH)
        except IOError, err:
            raise error.general('creating script: ' + name)
        except:
            if s is not None:
                s.close()
            raise
        if s is not None:
            s.close()

class build:
    """Build a package given a config file."""

    def _name_(self, name):
        #
        # If on Windows use shorter names to keep the build paths.
        #
        if options.host_windows:
            buildname = ''
            add = True
            for c in name:
                if c == '-':
                    add = True
                elif add:
                    buildname += c
                    add = False
            return buildname
        else:
            return name

    def _generate_report_(self, header, footer = None):
        ereport.generate('rsb-report-%s.txt' % self.macros['name'],
                         self.opts, header, footer)

    def __init__(self, name, create_tar_files, opts, macros = None):
        try:
            self.opts = opts
            if macros is None:
                self.macros = opts.defaults
            else:
                self.macros = macros
            self.create_tar_files = create_tar_files
            log.notice('config: ' + name)
            self.config = config.file(name, opts, self.macros)
            self.script = script()
            self.macros['buildname'] = self._name_(self.macros['name'])
        except error.general, gerr:
            log.notice(str(gerr))
            log.stderr('Build FAILED')
            raise
        except error.internal, ierr:
            log.notice(str(ierr))
            log.stderr('Internal Build FAILED')
            raise
        except:
            raise

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
        return self.config.defined('%{allow_cxc}') and \
            len(_host) and len(_build) and (_target) and \
            _host != _build and _host != _target

    def source(self, name):
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
            sm = self.macros.get(s, globals = False, maps = _map)
            if sm is None:
                raise error.internal('source macro not found: %s in %s (%s)' % \
                                         (s, name, _map))
            url = self.config.expand(sm[2])
            src = download.parse_url(url, '_sourcedir', self.config, self.opts)
            download.get_file(src['url'], src['local'], self.opts, self.config)
            if 'symlink' in src:
                sname = name.replace('-', '_')
                src['script'] = '%%{__ln_s} %s ${source_dir_%s}' % (src['symlink'], sname)
            elif 'compressed' in src:
                #
                # Zip files unpack as well so do not use tar.
                #
                src['script'] = '%s %s' % (src['compressed'], src['local'])
                if src['compressed-type'] != 'zip':
                    src['script'] += ' | %{__tar_extract} -'
            else:
                src['script'] = '%%{__tar_extract} %s' % (src['local'])
            srcs += [src]
        return srcs

    def source_setup(self, package, args):
        log.output('source setup: %s: %s' % (package.name(), ' '.join(args)))
        setup_name = args[1]
        args = args[1:]
        try:
            opts, args = getopt.getopt(args[1:], 'qDcn:ba')
        except getopt.GetoptError, ge:
            raise error.general('source setup error: %s' % str(ge))
        quiet = False
        unpack_before_chdir = True
        delete_before_unpack = True
        create_dir = False
        deleted_dir = False
        created_dir = False
        changed_dir = False
        opt_name = None
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
        name = None
        for source in self.source(setup_name):
            if name is None:
                if opt_name is None:
                    if source:
                        opt_name = source['name']
                    else:
                        raise error.general('setup source tag not found: %d' % (source_tag))
                else:
                    name = opt_name
            self.script.append(self.config.expand('cd %{_builddir}'))
            if not deleted_dir and  delete_before_unpack:
                self.script.append(self.config.expand('%{__rm} -rf ' + name))
                deleted_dir = True
            if not created_dir and create_dir:
                self.script.append(self.config.expand('%{__mkdir_p} ' + name))
                created_dir = True
            if not changed_dir and (not unpack_before_chdir or create_dir):
                self.script.append(self.config.expand('cd ' + name))
                changed_dir = True
            self.script.append(self.config.expand(source['script']))
        if not changed_dir and (unpack_before_chdir and not create_dir):
            self.script.append(self.config.expand('cd ' + name))
            changed_dir = True
        self.script.append(self.config.expand('%{__setup_post}'))

    def patch_setup(self, package, args):
        name = args[1]
        args = args[2:]
        _map = 'patch-%s' % (name)
        default_opts = ' '.join(args)
        patch_keys = [p for p in self.macros.map_keys(_map) if p != 'setup']
        patches = []
        for p in patch_keys:
            pm = self.macros.get(p, globals = False, maps = _map)
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
                raise error.general('patch URL not found: %s' % (' '.join(args)))
            if len(opts) == 0:
                opts = default_opts
            else:
                opts = ' '.join(opts)
            opts = self.config.expand(opts)
            url = self.config.expand(' '.join(url))
            #
            # Parse the URL first in the source builder's patch directory.
            #
            patch = download.parse_url(url, '_patchdir', self.config, self.opts)
            #
            # If not in the source builder package check the source directory.
            #
            if not path.exists(patch['local']):
                patch = download.parse_url(url, '_patchdir', self.config, self.opts)
            download.get_file(patch['url'], patch['local'], self.opts, self.config)
            if 'compressed' in patch:
                patch['script'] = patch['compressed'] + ' ' +  patch['local']
            else:
                patch['script'] = '%{__cat} ' + patch['local']
            patch['script'] += ' | %%{__patch} %s' % (opts)
            self.script.append(self.config.expand(patch['script']))

    def run(self, command, shell_opts = '', cwd = None):
        e = execute.capture_execution(log = log.default, dump = self.opts.quiet())
        cmd = self.config.expand('%{___build_shell} -ex ' + shell_opts + ' ' + command)
        log.output('run: ' + cmd)
        exit_code, proc, output = e.shell(cmd, cwd = path.host(cwd))
        if exit_code != 0:
            log.output('shell cmd failed: %s' % (cmd))
            raise error.general('building %s' % (self.macros['buildname']))

    def builddir(self):
        builddir = self.config.abspath('_builddir')
        self.rmdir(builddir)
        if not self.opts.dry_run():
            self.mkdir(builddir)

    def prep(self, package):
        self.script.append('echo "==> %prep:"')
        _prep = package.prep()
        if _prep:
            for l in _prep:
                args = l.split()
                if len(args):
                    def err(msg):
                        raise error.general('%s: %s' % (package, msg))
                    if args[0] == '%setup':
                        if len(args) == 1:
                            raise error.general('invalid %%setup directive: %s' % (' '.join(args)))
                        if args[1] == 'source':
                            self.source_setup(package, args[1:])
                        elif args[1] == 'patch':
                            self.patch_setup(package, args[1:])
                    elif args[0] in ['%patch', '%source']:
                        sources.process(args[0][1:], args[1:], self.macros, err)
                    elif args[0] == '%hash':
                        sources.hash(args[1:], self.macros, err)
                        self.hash(package, args)
                    else:
                        self.script.append(' '.join(args))

    def build(self, package):
        self.script.append('echo "==> clean %{buildroot}: ${SB_BUILD_ROOT}"')
        self.script.append('%s ${SB_BUILD_ROOT}' %
                           (self.config.expand('%{__rmdir}')))
        self.script.append('%s ${SB_BUILD_ROOT}' %
                           (self.config.expand('%{__mkdir_p}')))
        self.script.append('echo "==> %build:"')
        _build = package.build()
        if _build:
            for l in _build:
                self.script.append(l)

    def install(self, package):
        self.script.append('echo "==> %install:"')
        _install = package.install()
        if _install:
            for l in _install:
                args = l.split()
                self.script.append(' '.join(args))

    def files(self, package):
        if self.create_tar_files \
           and not self.macros.get('%{_disable_packaging'):
            self.script.append('echo "==> %files:"')
            inpath = path.abspath(self.config.expand('%{buildroot}'))
            tardir = path.abspath(self.config.expand('%{_tardir}'))
            self.script.append(self.config.expand('if test -d %s; then' % (inpath)))
            self.script.append(self.config.expand('  %%{__mkdir_p} %s' % tardir))
            self.script.append(self.config.expand('  cd ' + inpath))
            tar = path.join(tardir, package.long_name() + '.tar.bz2')
            cmd = self.config.expand('  %{__tar} -cf - . ' + '| %{__bzip2} > ' + tar)
            self.script.append(cmd)
            self.script.append(self.config.expand('  cd %{_builddir}'))
            self.script.append('fi')

    def clean(self, package):
        self.script.append('echo "==> %clean:"')
        _clean = package.clean()
        if _clean is not None:
            for l in _clean:
                args = l.split()
                self.script.append(' '.join(args))

    def build_package(self, package):
        if self.canadian_cross():
            self.script.append('echo "==> Candian-cross build/target:"')
            self.script.append('SB_CXC="yes"')
        else:
            self.script.append('SB_CXC="no"')
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

    def make(self):
        package = self.main_package()
        if package.disabled():
            log.notice('package: nothing to build')
        else:
            try:
                name = package.name()
                if self.canadian_cross():
                    log.notice('package: (Cxc) %s' % (name))
                else:
                    log.notice('package: %s' % (name))
                    log.trace('---- macro maps %s' % ('-' * 55))
                    log.trace('%s' % (str(self.config.macros)))
                    log.trace('-' * 70)
                self.script.reset()
                self.script.append(self.config.expand('%{___build_template}'))
                self.script.append('echo "=> ' + name + ':"')
                self.prep(package)
                self.build_package(package)
                if not self.opts.dry_run():
                    self.builddir()
                    sn = path.join(self.config.expand('%{_builddir}'), 'doit')
                    log.output('write script: ' + sn)
                    self.script.write(sn)
                    if self.canadian_cross():
                        log.notice('building: (Cxc) %s' % (name))
                    else:
                        log.notice('building: %s' % (name))
                    self.run(sn)
            except error.general, gerr:
                log.notice(str(gerr))
                log.stderr('Build FAILED')
                self._generate_report_('Build: %s' % (gerr))
                raise
            except error.internal, ierr:
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

    configs = { 'paths': [], 'files': [] }
    for cp in opts.defaults.expand('%{_configdir}').split(':'):
        hcp = path.host(path.abspath(cp))
        configs['paths'] += [hcp]
        configs['files'] += _scan(hcp, ['.cfg', '.bset'])
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
        optargs = { '--list-configs': 'List available configurations' }
        opts = options.load(args, optargs)
        log.notice('RTEMS Source Builder, Package Builder v%s' % (version.str()))
        if not check.host_setup(opts):
            if not opts.force():
                raise error.general('host build environment is not set up' +
                                    ' correctly (use --force to proceed)')
            log.notice('warning: forcing build with known host setup problems')
        if opts.get_arg('--list-configs'):
            configs = get_configs(opts)
            for p in configs['paths']:
                print 'Examining: %s' % (os.path.relpath(p))
                for c in configs['files']:
                    if c.endswith('.cfg'):
                        print '    %s' % (c)
        else:
            for config_file in opts.config_files():
                b = build(config_file, True, opts)
                b.make()
                b = None
    except error.general, gerr:
        log.stderr('Build FAILED')
        ec = 1
    except error.internal, ierr:
        log.stderr('Internal Build FAILED')
        ec = 1
    except error.exit, eerr:
        pass
    except KeyboardInterrupt:
        log.notice('abort: user terminated')
        ec = 1
    sys.exit(ec)

if __name__ == "__main__":
    run(sys.argv)
