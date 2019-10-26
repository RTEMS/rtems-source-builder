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
    import build
    import check
    import error
    import git
    import log
    import macros
    import path
    import sources
    import version
except KeyboardInterrupt:
    print('abort: user terminated', file = sys.stderr)
    sys.exit(1)
except:
    print('error: unknown application load error', file = sys.stderr)
    sys.exit(1)

#
# Define host profiles so it can simulated on another host.
#
host_profiles = {
    'darwin':  { '_os':              ('none',    'none',     'darwin'),
                 '_host':            ('triplet', 'required', 'x86_64-apple-darwin18.5.0'),
                 '_host_vendor':     ('none',    'none',     'apple'),
                 '_host_os':         ('none',    'none',     'darwin'),
                 '_host_os_version': ('none',    'none',     '18.5.0'),
                 '_host_cpu':        ('none',    'none',     'x86_64'),
                 '_host_alias':      ('none',    'none',     '%{nil}'),
                 '_host_arch':       ('none',    'none',     'x86_64'),
                 '_usr':             ('dir',     'optional', '/usr/local'),
                 '_var':             ('dir',     'optional', '/usr/local/var') },
    'freebsd': { '_os':              ('none',    'none',     'freebsd'),
                 '_host':            ('triplet', 'required', 'x86_64-freebsd12.0-RELEASE-p3'),
                 '_host_vendor':     ('none',    'none',     'pc'),
                 '_host_os':         ('none',    'none',     'freebsd'),
                 '_host_os_version': ('none',    'none',     '12.0-RELEASE-p3'),
                 '_host_cpu':        ('none',    'none',     'x86_64'),
                 '_host_alias':      ('none',    'none',     '%{nil}'),
                 '_host_arch':       ('none',    'none',     'x86_64'),
                 '_usr':             ('dir',     'optional', '/usr/local'),
                 '_var':             ('dir',     'optional', '/usr/local/var') },
    'linux':   { '_os':              ('none',    'none',     'linux'),
                 '_host':            ('triplet', 'required', 'x86_64-linux-gnu'),
                 '_host_vendor':     ('none',    'none',     'gnu'),
                 '_host_os':         ('none',    'none',     'linux'),
                 '_host_os_version': ('none',    'none',     '4.18.0-16'),
                 '_host_cpu':        ('none',    'none',     'x86_64'),
                 '_host_alias':      ('none',    'none',     '%{nil}'),
                 '_host_arch':       ('none',    'none',     'x86_64'),
                 '_usr':             ('dir',     'optional', '/usr/local'),
                 '_var':             ('dir',     'optional', '/usr/local/var') },
    'netbsd':  { '_os':              ('none',    'none',     'netbsd'),
                 '_host':            ('triplet', 'required', 'x86_64-netbsd8.0'),
                 '_host_vendor':     ('none',    'none',     'pc'),
                 '_host_os':         ('none',    'none',     'netbsd'),
                 '_host_os_version': ('none',    'none',     '8.0'),
                 '_host_cpu':        ('none',    'none',     'x86_64'),
                 '_host_alias':      ('none',    'none',     '%{nil}'),
                 '_host_arch':       ('none',    'none',     'x86_64'),
                 '_usr':             ('dir',     'optional', '/usr/local'),
                 '_var':             ('dir',     'optional', '/usr/local/var') },
    'solaris': { '_os':              ('none',    'none',     'solaris'),
                 '_host':            ('triplet', 'required', 'x86_64-pc-solaris2'),
                 '_host_vendor':     ('none',    'none',     'pc'),
                 '_host_os':         ('none',    'none',     'solaris'),
                 '_host_os_version': ('none',    'none',     '2'),
                 '_host_cpu':        ('none',    'none',     'x86_64'),
                 '_host_alias':      ('none',    'none',     '%{nil}'),
                 '_host_arch':       ('none',    'none',     'x86_64'),
                 '_usr':             ('dir',     'optional', '/usr/local'),
                 '_var':             ('dir',     'optional', '/usr/local/var') },
    'win32':   { '_os':              ('none',    'none',     'win32'),
                 '_windows_os':      ('none',    'none',     'mingw32'),
                 '_host':            ('triplet', 'required', 'x86_64-w64-mingw32'),
                 '_host_vendor':     ('none',    'none',     'pc'),
                 '_host_os':         ('none',    'none',     'win32'),
                 '_host_os_version': ('none',    'none',     '10'),
                 '_host_cpu':        ('none',    'none',     'x86_64'),
                 '_host_alias':      ('none',    'none',     '%{nil}'),
                 '_host_arch':       ('none',    'none',     'x86_64'),
                 '_usr':             ('dir',     'optional', '/usr/local'),
                 '_var':             ('dir',     'optional', '/usr/local/var') },
    'cygwin':  { '_os':              ('none',    'none',     'win32'),
                 '_windows_os':      ('none',    'none',     'cygwin'),
                 '_host':            ('triplet', 'required', 'x86_64-w64-cygwin'),
                 '_host_vendor':     ('none',    'none',     'microsoft'),
                 '_host_os':         ('none',    'none',     'win32'),
                 '_host_os_version': ('none',    'none',     '10'),
                 '_host_cpu':        ('none',    'none',     'x86_64'),
                 '_host_alias':      ('none',    'none',     '%{nil}'),
                 '_host_arch':       ('none',    'none',     'x86_64'),
                 '_usr':             ('dir',     'optional', '/usr/local'),
                 '_var':             ('dir',     'optional', '/usr/local/var') },
}

class log_capture(object):
    def __init__(self):
        self.log = []
        log.capture = self.capture

    def __str__(self):
        return os.linesep.join(self.log)

    def capture(self, text):
        self.log += [l for l in text.replace(chr(13), '').splitlines()]

    def get(self):
        return self.log

    def clear(self):
        self.log = []

#
# A skinny options command line class to get the configs to load.
#
class options(object):
    def __init__(self, argv, argopts, defaults):
        command_path = path.dirname(path.abspath(argv[1]))
        if len(command_path) == 0:
            command_path = '.'
        self.command_path = command_path
        self.command_name = path.basename(argv[0])
        extras = ['--dry-run',
                  '--with-download',
                  '--quiet',
                  '--without-log',
                  '--without-error-report',
                  '--without-release-url']
        self.argv = argv
        self.args = argv[1:] + extras
        self.defaults = macros.macros(name = defaults,
                                      sbdir = command_path)
        self.opts = { 'params' :  extras }
        self.sb_git()
        if argopts.download_dir is not None:
            self.defaults['_sourcedir'] = ('dir', 'optional', path.abspath(argopts.download_dir))
            self.defaults['_patchdir'] = ('dir', 'optional', path.abspath(argopts.download_dir))

    def parse_args(self, arg, error = True, extra = True):
        for a in range(0, len(self.args)):
            if self.args[a].startswith(arg):
                lhs = None
                rhs = None
                if '=' in self.args[a]:
                    eqs = self.args[a].split('=')
                    lhs = eqs[0]
                    if len(eqs) > 2:
                        rhs = '='.join(eqs[1:])
                    else:
                        rhs = eqs[1]
                elif extra:
                    lhs = self.args[a]
                    a += 1
                    if a < len(self.args):
                        rhs = self.args[a]
                return [lhs, rhs]
            a += 1
        return None

    def sb_git(self):
        repo = git.repo(self.defaults.expand('%{_sbdir}'), self)
        if repo.valid():
            repo_valid = '1'
            repo_head = repo.head()
            repo_clean = not repo.dirty()
            repo_remotes = '%{nil}'
            remotes = repo.remotes()
            if 'origin' in remotes:
                repo_remotes = '%s/origin' % (remotes['origin']['url'])
                repo_id = repo_head
            if not repo_clean:
                repo_id += '-modified'
                repo_mail = repo.email()
        else:
            repo_valid = '0'
            repo_head = '%{nil}'
            repo_clean = '%{nil}'
            repo_remotes = '%{nil}'
            repo_id = 'no-repo'
            repo_mail = None
        self.defaults['_sbgit_valid'] = repo_valid
        self.defaults['_sbgit_head']  = repo_head
        self.defaults['_sbgit_clean'] = str(repo_clean)
        self.defaults['_sbgit_remotes'] = str(repo_remotes)
        self.defaults['_sbgit_id']    = repo_id
        if repo_mail is not None:
            self.defaults['_sbgit_mail'] = repo_mail

    def get_arg(self, arg):
        if self.optargs is None or arg not in self.optargs:
            return None
        return self.parse_args(arg)

    def with_arg(self, label, default = 'not-found'):
        # the default if there is no option for without.
        result = default
        for pre in ['with', 'without']:
            arg_str = '--%s-%s' % (pre, label)
            arg_label = '%s_%s' % (pre, label)
            arg = self.parse_args(arg_str, error = False, extra = False)
            if arg is not None:
                if arg[1] is  None:
                    result = 'yes'
                else:
                    result = arg[1]
                break
        return [arg_label, result]

    def dry_run(self):
        return True

    def keep_going(self):
        return False

    def quiet(self):
            return True

    def no_clean(self):
        return True

    def always_clean(self):
        return False

    def no_install(self):
        return True

    def download_disabled(self):
        return False

    def disable_install(self):
        return True

    def urls(self):
        return None

    def info(self):
        s = ' Command Line: %s%s' % (' '.join(self.argv), os.linesep)
        s += ' Python: %s' % (sys.version.replace('\n', ''))
        return s

class buildset:
    """Build a set builds a set of packages."""

    def __init__(self, bset, _configs, opts, macros = None):
        log.trace('_bset: %s: init' % (bset))
        self.configs = _configs
        self.opts = opts
        if macros is None:
            self.macros = copy.copy(opts.defaults)
        else:
            self.macros = copy.copy(macros)
        self.macros.define('_rsb_get_source')
        log.trace('_bset: %s: macro defaults' % (bset))
        log.trace(str(self.macros))
        self.bset = bset
        _target = self.macros.expand('%{_target}')
        if len(_target):
            pkg_prefix = _target
        else:
            pkg_prefix = self.macros.expand('%{_host}')
        self.bset_pkg = '%s-%s-set' % (pkg_prefix, self.bset)
        self.build_failure = None

    def build_package(self, _config, _build):
        if not _build.disabled():
            _build.make()

    def parse(self, bset):

        #
        # Ouch, this is a copy of the setbuilder.py code.
        #

        def _clean(line):
            line = line[0:-1]
            b = line.find('#')
            if b >= 0:
                line = line[1:b]
            return line.strip()

        bsetname = bset

        if not path.exists(bsetname):
            for cp in self.macros.expand('%{_configdir}').split(':'):
                configdir = path.abspath(cp)
                bsetname = path.join(configdir, bset)
                if path.exists(bsetname):
                    break
                bsetname = None
            if bsetname is None:
                raise error.general('no build set file found: %s' % (bset))
        try:
            log.trace('_bset: %s: open: %s' % (self.bset, bsetname))
            bset = open(path.host(bsetname), 'r')
        except IOError as err:
            raise error.general('error opening bset file: %s' % (bsetname))

        configs = []

        try:
            lc = 0
            for l in bset:
                lc += 1
                l = _clean(l)
                if len(l) == 0:
                    continue
                log.trace('_bset: %s: %03d: %s' % (self.bset, lc, l))
                ls = l.split()
                if ls[0][-1] == ':' and ls[0][:-1] == 'package':
                    self.bset_pkg = ls[1].strip()
                    self.macros['package'] = self.bset_pkg
                elif ls[0][0] == '%':
                    def err(msg):
                        raise error.general('%s:%d: %s' % (self.bset, lc, msg))
                    if ls[0] == '%define':
                        if len(ls) > 2:
                            self.macros.define(ls[1].strip(),
                                               ' '.join([f.strip() for f in ls[2:]]))
                        else:
                            self.macros.define(ls[1].strip())
                    elif ls[0] == '%undefine':
                        if len(ls) > 2:
                            raise error.general('%s:%d: %undefine requires just the name' % \
                                                    (self.bset, lc))
                        self.macros.undefine(ls[1].strip())
                    elif ls[0] == '%include':
                        configs += self.parse(ls[1].strip())
                    elif ls[0] in ['%patch', '%source']:
                        sources.process(ls[0][1:], ls[1:], self.macros, err)
                    elif ls[0] == '%hash':
                        sources.hash(ls[1:], self.macros, err)
                else:
                    l = l.strip()
                    c = build.find_config(l, self.configs)
                    if c is None:
                        raise error.general('%s:%d: cannot find file: %s' % (self.bset, lc, l))
                    configs += [c]
        except:
            bset.close()
            raise

        bset.close()

        return configs

    def load(self):
        #
        # If the build set file ends with .cfg the user has passed to the
        # buildset builder a configuration so we just return it.
        #
        if self.bset.endswith('.cfg'):
            configs = [self.bset]
        else:
            exbset = self.macros.expand(self.bset)
            self.macros['_bset'] = exbset
            self.macros['_bset_tmp'] = build.short_name(exbset)
            root, ext = path.splitext(exbset)
            if exbset.endswith('.bset'):
                bset = exbset
            else:
                bset = '%s.bset' % (exbset)
            configs = self.parse(bset)
        return configs

    def set_host_details(self, host, opts, macros):
        if host not in host_profiles:
            raise error.general('invalid host: ' + host)
        for m in host_profiles[host]:
            opts.defaults[m] = host_profiles[host][m]
            macros[m] = host_profiles[host][m]
        macros_to_copy = [('%{_build}',        '%{_host}'),
                          ('%{_build_alias}',  '%{_host_alias}'),
                          ('%{_build_arch}',   '%{_host_arch}'),
                          ('%{_build_cpu}',    '%{_host_cpu}'),
                          ('%{_build_os}',     '%{_host_os}'),
                          ('%{_build_vendor}', '%{_host_vendor}')]
        for m in macros_to_copy:
            opts.defaults[m[0]] = opts.defaults[m[1]]
            macros[m[0]] = macros[m[1]]
        #
        # Look for a valid cc and cxx.
        #
        for cc in ['/usr/bin/cc', '/usr/bin/clang', '/usr/bin/gcc']:
            if check.check_exe(cc, cc):
                opts.defaults['__cc'] = cc
                macros['__cc'] = cc
                break
        if not macros.defined('__cc'):
            raise error.general('no valid cc found')
        for cxx in ['/usr/bin/c++', '/usr/bin/clang++', '/usr/bin/g++']:
            if check.check_exe(cxx, cxx):
                opts.defaults['__cxx'] = cxx
                macros['__cxx'] = cxx
        if not macros.defined('__cxx'):
            raise error.general('no valid c++ found')

    def build(self, host, nesting_count = 0):

        build_error = False

        nesting_count += 1

        log.trace('_bset: %s for %s: make' % (self.bset, host))
        log.notice('Build Set: %s for %s' % (self.bset, host))

        mail_subject = '%s on %s' % (self.bset,
                                     self.macros.expand('%{_host}'))

        current_path = os.environ['PATH']

        start = datetime.datetime.now()

        have_errors = False

        try:
            configs = self.load()

            log.trace('_bset: %s: configs: %s'  % (self.bset, ','.join(configs)))

            sizes_valid = False
            builds = []
            for s in range(0, len(configs)):
                b = None
                try:
                    #
                    # Each section of the build set gets a separate set of
                    # macros so we do not contaminate one configuration with
                    # another.
                    #
                    opts = copy.copy(self.opts)
                    macros = copy.copy(self.macros)
                    self.set_host_details(host, opts, macros)
                    if configs[s].endswith('.bset'):
                        log.trace('_bset: == %2d %s' % (nesting_count + 1, '=' * 75))
                        bs = buildset(configs[s], self.configs, opts, macros)
                        bs.build(host, nesting_count)
                        del bs
                    elif configs[s].endswith('.cfg'):
                        log.trace('_bset: -- %2d %s' % (nesting_count + 1, '-' * 75))
                        try:
                            b = build.build(configs[s],
                                            False,
                                            opts,
                                            macros)
                        except:
                            build_error = True
                            raise
                        self.build_package(configs[s], b)
                        builds += [b]
                        #
                        # Dump post build macros.
                        #
                        log.trace('_bset: macros post-build')
                        log.trace(str(macros))
                    else:
                        raise error.general('invalid config type: %s' % (configs[s]))
                except error.general as gerr:
                    have_errors = True
                    if b is not None:
                        if self.build_failure is None:
                            self.build_failure = b.name()
                    raise
            #
            # Clear out the builds ...
            #
            for b in builds:
                del b
        except error.general as gerr:
            if not build_error:
                log.stderr(str(gerr))
            raise
        except KeyboardInterrupt:
            raise
        except:
            self.build_failure = 'RSB general failure'
            raise
        finally:
            end = datetime.datetime.now()
            os.environ['PATH'] = current_path
            build_time = str(end - start)
            log.notice('Build Set: Time %s' % (build_time))

def list_bset_files(opts, configs):
    ext = '.bset'
    for p in configs['paths']:
        print('Examining: %s' % (os.path.relpath(p)))
    for c in configs['files']:
        if c.endswith(ext):
            print('    %s' % (c[:c.rfind('.')]))

def load_log(logfile):
    log.default = log.log(streams = [logfile])

def log_default():
    return 'rsb-log-getsource-%s.txt' % (datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))

def load_options(argv, argopts, defaults = '%{_sbdir}/defaults.mc'):
    opts = options(argv, argopts, defaults)
    opts.defaults['rtems_version'] = argopts.rtems_version
    return opts

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
                           default = log_default())
        argsp.add_argument('--trace', help = 'Enable trace logging for debugging.',
                           action = 'store_true')
        argsp.add_argument('bsets', nargs='*', help = 'Build sets.')

        argopts = argsp.parse_args(args[2:])

        load_log(argopts.log)
        log.notice('RTEMS Source Builder - Get Sources, %s' % (version.str()))
        log.tracing = argopts.trace

        opts = load_options(args, argopts)
        configs = build.get_configs(opts)

        if argopts.list_bsets:
            list_bset_files(opts, configs)
        else:
            if argopts.clean:
                if argopts.download_dir is None:
                    raise error.general('cleaning of the default download directories is not supported')
                if path.exists(argopts.download_dir):
                    log.notice('Cleaning source directory: %s' % (argopts.download_dir))
                    path.removeall(argopts.download_dir)
            if len(argopts.bsets) == 0:
                raise error.general('no build sets provided on the command line')
            for bset in argopts.bsets:
                get_sources_error = True
                b = buildset(bset, configs, opts)
                get_sources_error = False
                for host in host_profiles:
                    b.build(host)
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
