#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2012 Chris Johns (chrisj@rtems.org)
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

import check
import config
import defaults
import error
import execute
import log
import path

#
# Version of Sourcer Builder Build.
#
version = '0.1'

def removeall(path):

    def _onerror(function, path, excinfo):
        print 'removeall error: (%r) %s' % (function, path)

    shutil.rmtree(path, onerror = _onerror)
    return

def _notice(opts, text):
    if not opts.quiet() and not log.default.has_stdout():
        print text
    log.output(text)
    log.flush()

class script:
    """Create and manage a shell script."""

    def __init__(self, quiet = True):
        self.quiet = quiet
        self.reset()

    def reset(self):
        self.body = []
        self.lc = 0

    def append(self, text):
        if type(text) is str:
            text = text.splitlines()
        if not self.quiet:
            i = 0
            for l in text:
                i += 1
                log.output('script:%3d: ' % (self.lc + i) + l)
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

    def __init__(self, name, _defaults, opts):
        self.opts = opts
        _notice(opts, 'building: ' + name)
        self.config = config.file(name, _defaults = _defaults, opts = opts)
        self.script = script(quiet = opts.quiet())

    def _output(self, text):
        if not self.opts.quiet():
            log.output(text)

    def rmdir(self, rmpath):
        self._output('removing: %s' % (path.host(rmpath)))
        if not self.opts.dry_run():
            if path.exists(rmpath):
                removeall(rmpath)

    def mkdir(self, mkpath):
        self._output('making dir: %s' % (path.host(mkpath)))
        if not self.opts.dry_run():
            if os.name == 'nt':
                try:
                    os.makedirs(path.host(mkpath))
                except IOError, err:
                    _notice(self.opts, 'warning: cannot make directory: %s' % (mkpath))
                except OSError, err:
                    _notice(self.opts, 'warning: cannot make directory: %s' % (mkpath))
                except WindowsError, err:
                    _notice(self.opts, 'warning: cannot make directory: %s' % (mkpath))
            else:
                try:
                    os.makedirs(path.host(mkpath))
                except IOError, err:
                    _notice(self.opts, 'warning: cannot make directory: %s' % (mkpath))
                except OSError, err:
                    _notice(self.opts, 'warning: cannot make directory: %s' % (mkpath))

    def get_file(self, url, local):
        if local is None:
            raise error.general('source/patch path invalid')
        if not path.isdir(path.dirname(local)):
            if not self.opts.force():
                raise error.general('source path not found: %s; (--force to create)' \
                                        % (path.host(path.dirname(local))))
            self.mkdir(path.host(path.dirname(local)))
        if not path.exists(local):
            #
            # Not localy found so we need to download it. Check if a URL has
            # been provided on the command line.
            #
            url_bases = self.opts.urls()
            urls = []
            if url_bases is not None:
                for base in url_bases:
                    if base[-1:] != '/':
                        base += '/'
                    url_path = urlparse.urlsplit(url)[2]
                    slash = url_path.rfind('/')
                    if slash < 0:
                        url_file = url_path
                    else:
                        url_file = url_path[slash + 1:]
                    urls.append(urlparse.urljoin(base, url_file))
            urls.append(url)
            if self.opts.trace():
                print '_url:', ','.join(urls), '->', local
            for url in urls:
                #
                # Hack for GitHub.
                #
                if url.startswith('https://api.github.com'):
                    url = urlparse.urljoin(url, self.config.expand('tarball/%{version}'))
                _notice(self.opts, 'download: %s -> %s' % (url, os.path.relpath(path.host(local))))
                if not self.opts.dry_run():
                    failed = False
                    _in = None
                    _out = None
                    try:
                        _in = urllib2.urlopen(url)
                        _out = open(path.host(local), 'wb')
                        _out.write(_in.read())
                    except IOError, err:
                        msg = 'download: %s: error: %s' % (url, str(err))
                        _notice(self.opts, msg)
                        if path.exists(local):
                            os.remove(path.host(local))
                        failed = True
                    except ValueError, err:
                        msg = 'download: %s: error: %s' % (url, str(err))
                        _notice(self.opts, msg)
                        if path.exists(local):
                            os.remove(path.host(local))
                        failed = True
                    except:
                        msg = 'download: %s: error' % (url)
                        print >> sys.stderr, msg
                        if _out is not None:
                            _out.close()
                        raise
                    if _out is not None:
                        _out.close()
                    if _in is not None:
                        del _in
                    if not failed:
                        if not path.isfile(local):
                            raise error.general('source is not a file: %s' % (path.host(local)))
                        return
            if not self.opts.dry_run():
                raise error.general('downloading %s: all paths have failed, giving up' % (url))

    def parse_url(self, url, pathkey):
        #
        # Split the source up into the parts we need.
        #
        source = {}
        source['url'] = url
        source['path'] = path.dirname(url)
        source['file'] = path.basename(url)
        source['name'], source['ext'] = path.splitext(source['file'])
        #
        # Get the file. Checks the local source directory first.
        #
        source['local'] = None
        for p in self.config.define(pathkey).split(':'):
            local = path.join(path.abspath(p), source['file'])
            if source['local'] is None:
                source['local'] = local
            if path.exists(local):
                source['local'] = local
                break
        #
        # Is the file compressed ?
        #
        esl = source['ext'].split('.')
        if esl[-1:][0] == 'gz':
            source['compressed'] = '%{__gzip} -dc'
        elif esl[-1:][0] == 'bz2':
            source['compressed'] = '%{__bzip2} -dc'
        elif esl[-1:][0] == 'bz2':
            source['compressed'] = '%{__zip} -u'
        elif esl[-1:][0] == 'xz':
            source['compressed'] = '%{__xz} -dc'
        source['script'] = ''
        return source

    def source(self, package, source_tag):
        #
        # Scan the sources found in the config file for the one we are
        # after. Infos or tags are lists.
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
        source = self.parse_url(url, '_sourcedir')
        self.get_file(source['url'], source['local'])
        if 'compressed' in source:
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
        patch = self.parse_url(url, '_patchdir')
        #
        # If not in the source builder package check the source directory.
        #
        if not path.exists(patch['local']):
            patch = self.parse_url(url, '_sourcedir')
        self.get_file(patch['url'], patch['local'])
        if 'compressed' in patch:
            patch['script'] = patch['compressed'] + ' ' +  patch['local']
        else:
            patch['script'] = '%{__cat} ' + patch['local']
        patch['script'] += ' | %{__patch} ' + ' '.join(args[1:])
        self.script.append(self.config.expand(patch['script']))

    def setup(self, package, args):
        self._output('prep: %s: %s' % (package.name(), ' '.join(args)))
        opts, args = getopt.getopt(args[1:], 'qDcTn:b:a:')
        source_tag = 0
        quiet = False
        unpack_default_source = True
        delete_before_unpack = True
        create_dir = False
        name = None
        unpack_before_chdir = True
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
                    raise error.general('setup source tag no a number: %s' % (o[1]))
                source_tag = int(o[1])
            elif o[0] == '-a':
                unpack_before_chdir = False
                source_tag = int(o[1])
        source0 = None
        source = self.source(package, source_tag)
        if name is None:
            if source:
                name = source['name']
            else:
                name = source0['name']
        self.script.append(self.config.expand('cd %{_builddir}'))
        if delete_before_unpack:
            self.script.append(self.config.expand('%{__rm} -rf ' + name))
        if create_dir:
            self.script.append(self.config.expand('%{__mkdir_p} ' + name))
        #
        # If -a? then change directory before unpacking.
        #
        if not unpack_before_chdir:
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
        if unpack_before_chdir:
            self.script.append(self.config.expand('cd ' + name))
        self.script.append(self.config.expand('%{__setup_post}'))
        if create_dir:
            self.script.append(self.config.expand('cd ..'))

    def run(self, command, shell_opts = '', cwd = None):
        e = execute.capture_execution(log = log.default, dump = self.opts.quiet())
        cmd = self.config.expand('%{___build_shell} -ex ' + shell_opts + ' ' + command)
        self._output('run: ' + cmd)
        exit_code, proc, output = e.shell(cmd, cwd = path.host(cwd))
        if exit_code != 0:
            raise error.general('shell cmd failed: ' + cmd)

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
        self.script.append('echo "==> %files:"')
        prefixbase = self.opts.prefixbase()
        if prefixbase is None:
            prefixbase = ''
        inpath = path.join('%{buildroot}', prefixbase)
        tardir = path.abspath(self.config.expand('%{_tardir}'))
        self.script.append(self.config.expand('if test -d %s; then' % (inpath)))
        self.script.append('  mkdir -p %s' % tardir)
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

    def cleanup(self):
        if not self.opts.no_clean():
            buildroot = self.config.abspath('buildroot')
            builddir = self.config.abspath('_builddir')
            tmproot = self.config.abspath('_tmproot')
            if self.opts.trace():
                _notice(self.opts, 'cleanup: %s' % (buildroot))
            self.rmdir(buildroot)
            if self.opts.trace():
                _notice(self.opts, 'cleanup: %s' % (builddir))
            self.rmdir(builddir)
            if self.opts.trace():
                _notice(self.opts, 'cleanup: %s' % (tmproot))
            self.rmdir(tmproot)

    def make(self):
        packages = self.config.packages()
        package = packages['main']
        name = package.name()
        _notice(self.opts, 'package: %s' % (name))
        self.script.reset()
        self.script.append(self.config.expand('%{___build_template}'))
        self.script.append('echo "=> ' + name + ':"')
        self.prep(package)
        self.build(package)
        self.install(package)
        self.files(package)
        if not self.opts.no_clean():
            self.clean(package)
        if not self.opts.dry_run():
            self.builddir()
            sn = path.join(self.config.expand('%{_builddir}'), 'doit')
            self._output('write script: ' + sn)
            self.script.write(sn)
            _notice(self.opts, 'building: ' + name)
            self.run(sn)

    def name(self):
        packages = self.config.packages()
        package = packages['main']
        return package.name()

def get_configs(opts, _defaults):

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
    for cp in opts.expand('%{_configdir}', _defaults).split(':'):
        configs['paths'] += [path.host(path.abspath(cp))]
        configs['files'] += _scan(cp, ['.cfg', '.bset'])
    configs['files'] = sorted(configs['files'])
    return configs

def run(args):
    try:
        optargs = { '--list-configs': 'List available configurations' }
        opts, _defaults = defaults.load(args, optargs)
        log.default = log.log(opts.logfiles())
        _notice(opts, 'Source Builder, Package Builder v%s' % (version))
        if not check.host_setup(opts, _defaults):
            if not opts.force():
                raise error.general('host build environment is not set up correctly (use --force to proceed)')
            _notice(opts, 'warning: forcing build with known host setup problems')
        if opts.get_arg('--list-configs'):
            list_configs(opts, _defaults)
        else:
            for config_file in opts.config_files():
                b = build(config_file, _defaults = _defaults, opts = opts)
                b.make()
                del b
    except error.general, gerr:
        print gerr
        sys.exit(1)
    except error.internal, ierr:
        print ierr
        sys.exit(1)
    except error.exit, eerr:
        pass
    except KeyboardInterrupt:
        _notice(opts, 'user terminated')
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    run(sys.argv)
