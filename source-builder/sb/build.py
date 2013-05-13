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
    import execute
    import log
    import options
    import path
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

    def __init__(self, name, create_tar_files, opts, macros = None):
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

    def rmdir(self, rmpath):
        log.output('removing: %s' % (path.host(rmpath)))
        if not self.opts.dry_run():
            if path.exists(rmpath):
                path.removeall(rmpath)

    def mkdir(self, mkpath):
        log.output('making dir: %s' % (path.host(mkpath)))
        if not self.opts.dry_run():
            path.mkdir(mkpath)

    def source(self, package, source_tag):
        #
        # Scan the sources found in the config file for the one we are
        # after. Infos or tags are lists. Merge in any macro defined
        # sources as these may be overridden by user loaded macros.
        #
        sources = package.sources()
        url = None
        for s in sources:
            tag = s[len('source'):]
            if tag.isdigit():
                if int(tag) == source_tag:
                    url = sources[s][0]
                    break
        if url is None:
            raise error.general('source tag not found: source%d' % (source_tag))
        source = download.parse_url(url, '_sourcedir', self.config, self.opts)
        download.get_file(source['url'], source['local'], self.opts, self.config)
        if 'symlink' in source:
            source['script'] = '%%{__ln_s} %s ${source_dir_%d}' % (source['symlink'], source_tag)
        elif 'compressed' in source:
            source['script'] = source['compressed'] + ' ' + \
                source['local'] + ' | %{__tar_extract} -'
        else:
            source['script'] = '%{__tar_extract} ' + source['local']
        return source

    def patch(self, package, args):
        #
        # Scan the patches found in the config file for the one we are
        # after. Infos or tags are lists.
        #
        patches = package.patches()
        url = None
        for p in patches:
            if args[0][1:].lower() == p:
                url = patches[p][0]
                break
        if url is None:
            raise error.general('patch tag not found: %s' % (args[0]))
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
        patch['script'] += ' | %{__patch} ' + ' '.join(args[1:])
        self.script.append(self.config.expand(patch['script']))

    def canadian_cross(self):
        _host = self.config.expand('%{_host}')
        _build = self.config.expand('%{_build}')
        _target = self.config.expand('%{_target}')
        return self.config.defined('%{allow_cxc}') and \
            _host != _build and _host != _target

    def setup(self, package, args):
        log.output('prep: %s: %s' % (package.name(), ' '.join(args)))
        opts, args = getopt.getopt(args[1:], 'qDcTn:b:a:')
        source_tag = 0
        quiet = False
        unpack_default_source = True
        unpack_before_chdir = True
        delete_before_unpack = True
        create_dir = False
        name = None
        for o in opts:
            if o[0] == '-q':
                quiet = True
            elif o[0] == '-D':
                delete_before_unpack = False
            elif o[0] == '-c':
                create_dir = True
            elif o[0] == '-T':
                unpack_default_source = False
            elif o[0] == '-n':
                name = o[1]
            elif o[0] == '-b':
                unpack_before_chdir = True
                if not o[1].isdigit():
                    raise error.general('setup -b source tag is not a number: %s' % (o[1]))
                source_tag = int(o[1])
            elif o[0] == '-a':
                unpack_before_chdir = False
                if not o[1].isdigit():
                    raise error.general('setup -a source tag is not a number: %s' % (o[1]))
                source_tag = int(o[1])
        source0 = None
        source = self.source(package, source_tag)
        if name is None:
            if source:
                name = source['name']
            else:
                raise error.general('setup source tag not found: %d' % (source_tag))
        name = self._name_(name)
        self.script.append(self.config.expand('cd %{_builddir}'))
        if delete_before_unpack:
            self.script.append(self.config.expand('%{__rm} -rf ' + name))
        if create_dir:
            self.script.append(self.config.expand('%{__mkdir_p} ' + name))
        #
        # If -a? then change directory before unpacking.
        #
        if not unpack_before_chdir or create_dir:
            self.script.append(self.config.expand('cd ' + name))
        #
        # Unpacking the source. Note, treated the same as -a0.
        #
        if unpack_default_source and source_tag != 0:
            source0 = self.source(package, 0)
            if source0 is None:
                raise error.general('no setup source0 tag found')
            self.script.append(self.config.expand(source0['script']))
        self.script.append(self.config.expand(source['script']))
        if unpack_before_chdir and not create_dir:
            self.script.append(self.config.expand('cd ' + name))
        self.script.append(self.config.expand('%{__setup_post}'))

    def run(self, command, shell_opts = '', cwd = None):
        e = execute.capture_execution(log = log.default, dump = self.opts.quiet())
        cmd = self.config.expand('%{___build_shell} -ex ' + shell_opts + ' ' + command)
        log.output('run: ' + cmd)
        exit_code, proc, output = e.shell(cmd, cwd = path.host(cwd))
        if exit_code != 0:
            raise error.general('shell cmd failed: %s' % (cmd))

    def builddir(self):
        builddir = self.config.abspath('_builddir')
        self.rmdir(builddir)
        if not self.opts.dry_run():
            self.mkdir(builddir)

    def prep(self, package):
        self.script.append('echo "==> %prep:"')
        _prep = package.prep()
        for l in _prep:
            args = l.split()
            if args[0] == '%setup':
                self.setup(package, args)
            elif args[0].startswith('%patch'):
                self.patch(package, args)
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
        for l in _build:
            args = l.split()
            self.script.append(' '.join(args))

    def install(self, package):
        self.script.append('echo "==> %install:"')
        _install = package.install()
        for l in _install:
            args = l.split()
            self.script.append(' '.join(args))

    def files(self, package):
        if self.create_tar_files:
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
        if not self.opts.no_clean():
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

    def name(self):
        packages = self.config.packages()
        package = packages['main']
        return package.name()

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
    configs['files'] = sorted(configs['files'])
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
                del b
    except error.general, gerr:
        print gerr
        print >> sys.stderr, 'Build FAILED'
        sys.exit(1)
    except error.internal, ierr:
        print ierr
        print >> sys.stderr, 'Build FAILED'
        sys.exit(1)
    except error.exit, eerr:
        pass
    except KeyboardInterrupt:
        log.notice('abort: user terminated')
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    run(sys.argv)
