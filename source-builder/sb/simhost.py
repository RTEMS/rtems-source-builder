#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2020 Chris Johns (chrisj@rtems.org)
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

import copy
import datetime
import os

try:
    from . import build
    from . import check
    from . import error
    from . import git
    from . import log
    from . import macros
    from . import path
    from . import shell
    from . import sources
    from . import version
except KeyboardInterrupt:
    print('abort: user terminated', file=sys.stderr)
    sys.exit(1)
except:
    raise

#
# Define host profiles so it can simulated on another host.
#
profiles = {
    'darwin': {
        '_os': ('none', 'none', 'darwin'),
        '_host': ('triplet', 'required', 'x86_64-apple-darwin18.5.0'),
        '_host_vendor': ('none', 'none', 'apple'),
        '_host_os': ('none', 'none', 'darwin'),
        '_host_os_version': ('none', 'none', '18.5.0'),
        '_host_cpu': ('none', 'none', 'x86_64'),
        '_host_alias': ('none', 'none', '%{nil}'),
        '_host_arch': ('none', 'none', 'x86_64'),
        '_usr': ('dir', 'optional', '/usr/local'),
        '_var': ('dir', 'optional', '/usr/local/var')
    },
    'freebsd': {
        '_os': ('none', 'none', 'freebsd'),
        '_host': ('triplet', 'required', 'x86_64-freebsd12.0-RELEASE-p3'),
        '_host_vendor': ('none', 'none', 'pc'),
        '_host_os': ('none', 'none', 'freebsd'),
        '_host_os_version': ('none', 'none', '12.0-RELEASE-p3'),
        '_host_cpu': ('none', 'none', 'x86_64'),
        '_host_alias': ('none', 'none', '%{nil}'),
        '_host_arch': ('none', 'none', 'x86_64'),
        '_usr': ('dir', 'optional', '/usr/local'),
        '_var': ('dir', 'optional', '/usr/local/var')
    },
    'linux': {
        '_os': ('none', 'none', 'linux'),
        '_host': ('triplet', 'required', 'x86_64-linux-gnu'),
        '_host_vendor': ('none', 'none', 'gnu'),
        '_host_os': ('none', 'none', 'linux'),
        '_host_os_version': ('none', 'none', '4.18.0-16'),
        '_host_cpu': ('none', 'none', 'x86_64'),
        '_host_alias': ('none', 'none', '%{nil}'),
        '_host_arch': ('none', 'none', 'x86_64'),
        '_usr': ('dir', 'optional', '/usr/local'),
        '_var': ('dir', 'optional', '/usr/local/var')
    },
    'netbsd': {
        '_os': ('none', 'none', 'netbsd'),
        '_host': ('triplet', 'required', 'x86_64-netbsd8.0'),
        '_host_vendor': ('none', 'none', 'pc'),
        '_host_os': ('none', 'none', 'netbsd'),
        '_host_os_version': ('none', 'none', '8.0'),
        '_host_cpu': ('none', 'none', 'x86_64'),
        '_host_alias': ('none', 'none', '%{nil}'),
        '_host_arch': ('none', 'none', 'x86_64'),
        '_usr': ('dir', 'optional', '/usr/local'),
        '_var': ('dir', 'optional', '/usr/local/var')
    },
    'solaris': {
        '_os': ('none', 'none', 'solaris'),
        '_host': ('triplet', 'required', 'x86_64-pc-solaris2'),
        '_host_vendor': ('none', 'none', 'pc'),
        '_host_os': ('none', 'none', 'solaris'),
        '_host_os_version': ('none', 'none', '2'),
        '_host_cpu': ('none', 'none', 'x86_64'),
        '_host_alias': ('none', 'none', '%{nil}'),
        '_host_arch': ('none', 'none', 'x86_64'),
        '_usr': ('dir', 'optional', '/usr/local'),
        '_var': ('dir', 'optional', '/usr/local/var')
    },
    'win32': {
        '_os': ('none', 'none', 'win32'),
        '_windows_os': ('none', 'none', 'mingw32'),
        '_host': ('triplet', 'required', 'x86_64-w64-mingw32'),
        '_host_vendor': ('none', 'none', 'pc'),
        '_host_os': ('none', 'none', 'win32'),
        '_host_os_version': ('none', 'none', '10'),
        '_host_cpu': ('none', 'none', 'x86_64'),
        '_host_alias': ('none', 'none', '%{nil}'),
        '_host_arch': ('none', 'none', 'x86_64'),
        '_usr': ('dir', 'optional', '/usr/local'),
        '_var': ('dir', 'optional', '/usr/local/var')
    },
    'cygwin': {
        '_os': ('none', 'none', 'win32'),
        '_windows_os': ('none', 'none', 'cygwin'),
        '_host': ('triplet', 'required', 'x86_64-w64-cygwin'),
        '_host_vendor': ('none', 'none', 'microsoft'),
        '_host_os': ('none', 'none', 'win32'),
        '_host_os_version': ('none', 'none', '10'),
        '_host_cpu': ('none', 'none', 'x86_64'),
        '_host_alias': ('none', 'none', '%{nil}'),
        '_host_arch': ('none', 'none', 'x86_64'),
        '_usr': ('dir', 'optional', '/usr/local'),
        '_var': ('dir', 'optional', '/usr/local/var')
    },
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


def find_bset_config(bset_config, macros):
    '''Find the build set or config file using the macro config defined path.'''
    name = bset_config
    if not path.exists(name):
        for cp in macros.expand('%{_configdir}').split(':'):
            configdir = path.abspath(cp)
            name = path.join(configdir, bset_config)
            if path.exists(name):
                break
            name = None
        if name is None:
            raise error.general('no build set file found: %s' % (bset_config))
    return name


def macro_expand(macros, _str):
    cstr = None
    while cstr != _str:
        cstr = _str
        _str = macros.expand(_str)
        _str = shell.expand(macros, _str)
    return _str


def strip_common_prefix(files):
    commonprefix = os.path.commonprefix(files)
    return sorted(list(set([f[len(commonprefix):] for f in files])))


#
# A skinny options command line class to get the configs to load.
#
class options(object):

    default_extras = {
        '_dry_run': '1'
    }

    def __init__(self, argv, argopts, defaults, extras):
        command_path = path.dirname(path.abspath(argv[0]))
        if len(command_path) == 0:
            command_path = '.'
        self.command_path = command_path
        self.command_name = path.basename(argv[0])
        extras += [
            '--dry-run', '--quiet', '--without-log', '--without-error-report',
            '--without-release-url'
        ]
        self.argv = argv
        self.args = argv[1:] + extras
        self.defaults = macros.macros(name=defaults, sbdir=command_path)
        self.load_overrides()
        self.opts = {'params': extras}
        self.sb_git()
        self.rtems_bsp()
        for de in options.default_extras:
            self.defaults[de] = options.default_extras[de]
        if 'download_dir' in argopts and argopts.download_dir is not None:
            self.defaults['_sourcedir'] = ('dir', 'optional',
                                           path.abspath(argopts.download_dir))
            self.defaults['_patchdir'] = ('dir', 'optional',
                                          path.abspath(argopts.download_dir))

    def load_overrides(self):
        overrides = None
        if os.name == 'nt':
            try:
                from . import windows
                overrides = windows.load()
                host_windows = True
                host_posix = False
            except:
                raise error.general('failed to load Windows host support')
        elif os.name == 'posix':
            uname = os.uname()
            try:
                if uname[0].startswith('MINGW64_NT'):
                    from . import windows
                    overrides = windows.load()
                    host_windows = True
                elif uname[0].startswith('CYGWIN_NT'):
                    from . import windows
                    overrides = windows.load()
                elif uname[0] == 'Darwin':
                    from . import darwin
                    overrides = darwin.load()
                elif uname[0] == 'FreeBSD':
                    from . import freebsd
                    overrides = freebsd.load()
                elif uname[0] == 'NetBSD':
                    from . import netbsd
                    overrides = netbsd.load()
                elif uname[0] == 'Linux':
                    from . import linux
                    overrides = linux.load()
                elif uname[0] == 'SunOS':
                    from . import solaris
                    overrides = solaris.load()
            except error.general as ge:
                raise error.general('failed to load %s host support: %s' %
                                    (uname[0], ge))
            except:
                raise error.general('failed to load %s host support' %
                                    (uname[0]))
        else:
            raise error.general('unsupported host type; please add')
        if overrides is None:
            raise error.general('no hosts defaults found; please add')
        for k in overrides:
            self.defaults[k] = overrides[k]

    def parse_args(self, arg, error=True, extra=True):
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

    def rtems_bsp(self, arch='arch'):
        self.defaults['rtems_version'] = str(version.version())
        self.defaults['_target'] = arch + '-rtems'
        self.defaults['rtems_host'] = 'rtems-' + arch
        self.defaults['with_rtems_bsp'] = 'rtems-bsp'

    def sb_git(self):
        repo = git.repo(self.defaults.expand('%{_sbdir}'), self)
        repo_mail = None
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
        self.defaults['_sbgit_valid'] = repo_valid
        self.defaults['_sbgit_head'] = repo_head
        self.defaults['_sbgit_clean'] = str(repo_clean)
        self.defaults['_sbgit_remotes'] = str(repo_remotes)
        self.defaults['_sbgit_id'] = repo_id
        if repo_mail is not None:
            self.defaults['_sbgit_mail'] = repo_mail

    def get_arg(self, arg):
        if self.optargs is None or arg not in self.optargs:
            return None
        return self.parse_args(arg)

    def with_arg(self, label, default='not-found'):
        # the default if there is no option for without.
        result = default
        for pre in ['with', 'without']:
            arg_str = '--%s-%s' % (pre, label)
            arg_label = '%s_%s' % (pre, label)
            arg = self.parse_args(arg_str, error=False, extra=False)
            if arg is not None:
                if arg[1] is None:
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

    def trace(self):
        return False

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

    def __init__(self, bset, _configs, opts, macros=None):
        log.trace('_bset: %s: init' % (bset))
        self.parent = 'root'
        self._includes = []
        self._errors = []
        self.configs = _configs
        self.opts = opts
        if macros is None:
            self.macros = copy.copy(opts.defaults)
        else:
            self.macros = copy.copy(macros)
        self.macros.define('_rsb_getting_source')
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

    def _add_includes(self, includes, parent=None):
        if parent is None:
            parent = self.parent
        if not isinstance(includes, list):
            includes = [includes]
        self._includes += [i + ':' + parent for i in includes]

    def _rebase_includes(self, includes, parent):
        if not isinstance(includes, list):
            includes = [includes]
        rebased = []
        for i in includes:
            if i.split(':', 2)[1] == 'root':
                rebased += [i.split(':', 2)[0] + ':' + parent]
            else:
                rebased += [i]
        return rebased

    def root(self):
        for i in self._includes:
            si = i.split(':')
            if len(si) == 2:
                if si[1] == 'root':
                    return si[0]
        return None

    def includes(self):
        return [i for i in self._includes if not i.endswith(':root')]

    def deps(self):
        return strip_common_prefix([i.split(':')[0] for i in self.includes()])

    def errors(self):
        return sorted(list(set(self._errors)))

    def build_package(self, _config, _build):
        if not _build.disabled():
            _build.make()

    def parse(self, bset, expand=True):

        #
        # Ouch, this is a copy of the setbuilder.py code.
        #

        def _clean(line):
            line = line[0:-1]
            b = line.find('#')
            if b >= 0:
                line = line[1:b]
            return line.strip()

        bsetname = find_bset_config(bset, self.macros)

        try:
            log.trace('_bset: %s: open: %s %s' % (self.bset, bsetname, expand))
            bsetf = open(path.host(bsetname), 'r')
        except IOError as err:
            raise error.general('error opening bset file: %s' % (bsetname))

        self._add_includes(bsetname)
        parent = self.parent
        self.parent = bsetname

        configs = []

        try:
            lc = 0
            for l in bsetf:
                lc += 1
                l = _clean(l)
                if len(l) == 0:
                    continue
                log.trace('_bset: %s: %03d: %s' % (self.bset, lc, l))
                ls = l.split()
                if ls[0][-1] == ':' and ls[0][:-1] == 'package':
                    self.bset_pkg = ls[1].strip()
                    self.macros['package'] = self.bset_pkg
                elif ls[0][0] == '%' and (len(ls[0]) > 1 and ls[0][1] != '{'):

                    def err(msg):
                        raise error.general('%s:%d: %s' % (self.bset, lc, msg))

                    if ls[0] == '%define' or ls[0] == '%defineifnot':
                        name = ls[1].strip()
                        value = None
                        if len(ls) > 2:
                            value = ' '.join([f.strip() for f in ls[2:]])
                        if ls[0] == '%defineifnot':
                            if self.macros.defined(name):
                                name = None
                        if name is not None:
                            if value is not None:
                                self.macros.define(name, value)
                            else:
                                self.macros.define(name)
                    elif ls[0] == '%undefine':
                        if len(ls) > 2:
                            raise error.general('%s:%d: %undefine requires ' \
                                                'just the name' % (self.bset, lc))
                        self.macros.undefine(ls[1].strip())
                    elif ls[0] == '%include':
                        configs += self.parse(ls[1].strip())
                    elif ls[0] in ['%patch', '%source']:
                        sources.process(ls[0][1:], ls[1:], self.macros, err)
                    elif ls[0] == '%hash':
                        sources.hash(ls[1:], self.macros, err)
                else:
                    try:
                        l = macro_expand(self.macros, l.strip())
                    except:
                        if expand:
                            raise
                        l = None
                    if l is not None:
                        c = build.find_config(l, self.configs)
                        if c is None:
                            raise error.general('%s:%d: cannot find file: %s' %
                                                (self.bset, lc, l))
                        configs += [c + ':' + self.parent]
        finally:
            bsetf.close()
            self.parent = parent

        return configs

    def load(self):
        #
        # If the build set file ends with .cfg the user has passed to the
        # buildset builder a configuration so we just return it.
        #
        if self.bset.endswith('.cfg'):
            self._add_includes(self.bset)
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
        if host not in profiles:
            raise error.general('invalid host: ' + host)
        for m in profiles[host]:
            opts.defaults[m] = profiles[host][m]
            macros[m] = profiles[host][m]
        macros_to_copy = [('%{_build}', '%{_host}'),
                          ('%{_build_alias}', '%{_host_alias}'),
                          ('%{_build_arch}', '%{_host_arch}'),
                          ('%{_build_cpu}', '%{_host_cpu}'),
                          ('%{_build_os}', '%{_host_os}'),
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

    def build(self, host, nesting_count=0):

        build_error = False

        nesting_count += 1

        log.trace('_bset: %2d: %s for %s: make' %
                  (nesting_count, self.bset, host))
        log.notice('Build Set: %s for %s' % (self.bset, host))

        mail_subject = '%s on %s' % (self.bset, self.macros.expand('%{_host}'))

        current_path = os.environ['PATH']

        start = datetime.datetime.now()

        have_errors = False

        try:
            configs = self.load()

            log.trace('_bset: %2d: %s: configs: %s' %
                      (nesting_count, self.bset, ','.join(configs)))

            sizes_valid = False
            builds = []
            for s in range(0, len(configs)):
                bs = None
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
                    config, parent = configs[s].split(':', 2)
                    if config.endswith('.bset'):
                        log.trace('_bset: %2d: %s' %
                                  (nesting_count + 1, '=' * 75))
                        bs = buildset(config, self.configs, opts, macros)
                        bs.build(host, nesting_count)
                        self._includes += \
                            self._rebase_includes(bs.includes(), parent)
                        del bs
                    elif config.endswith('.cfg'):
                        log.trace('_bset: %2d: %s' %
                                  (nesting_count + 1, '-' * 75))
                        try:
                            b = build.build(config, False, opts, macros)
                            self._includes += \
                                self._rebase_includes(b.includes(), parent)
                        except:
                            build_error = True
                            raise
                        self.build_package(config, b)
                        builds += [b]
                        #
                        # Dump post build macros.
                        #
                        log.trace('_bset: %2d: macros post-build' %
                                  (nesting_count))
                        log.trace(str(macros))
                    else:
                        raise error.general('invalid config type: %s' %
                                            (config))
                except error.general as gerr:
                    have_errors = True
                    if b is not None:
                        if self.build_failure is None:
                            self.build_failure = b.name()
                        self._includes += b.includes()
                    self._errors += \
                        [find_bset_config(config, opts.defaults) + ':' + parent] + self._includes
                    raise
            #
            # Clear out the builds ...
            #
            for b in builds:
                del b
            self._includes += \
                [find_bset_config(c.split(':')[0], self.macros) + ':' + self.bset for c in configs]
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


def list_hosts():
    hosts = sorted(profiles.keys())
    max_os_len = max(len(h) for h in hosts)
    max_host_len = max(len(profiles[h]['_host'][2]) for h in hosts)
    for h in hosts:
        log.notice('%*s: %-*s %s' %
                   (max_os_len, h, max_host_len, profiles[h]['_host'][2],
                    profiles[h]['_host'][2]))


def get_files(configs, ext, localpath):
    files = []
    if localpath:
        for cp in configs['localpaths']:
            files += [c for c in configs[cp] if c.endswith(ext)]
    else:
        files = [c for c in configs['files'] if c.endswith(ext)]
    return files


def get_config_files(configs, localpath=False):
    return get_files(configs, '.cfg', localpath)


def get_bset_files(configs, localpath=False):
    return get_files(configs, '.bset', localpath)


def get_config_bset_files(opts, configs):
    cbs = get_config_files(configs) + get_bset_files(configs)
    return strip_common_prefix(
        [find_bset_config(cb, opts.defaults) for cb in cbs])


def get_root_bset_files(opts, configs, localpath=False):
    bsets = get_bset_files(configs, localpath)
    incs = {}
    for bs in bsets:
        bset = buildset(bs, configs, opts)
        cfgs = [
            find_bset_config(c.split(':')[0], bset.macros)
            for c in bset.parse(bs, False)
        ]
        incs[bset.root()] = bset.includes() + cfgs
    roots = sorted(incs.keys())
    for inc in incs:
        for i in incs[inc]:
            si = i.split(':')
            if len(si) > 0 and si[0] in roots:
                roots.remove(si[0])
    return roots


def get_root(configs):
    return configs['root']


def list_root_bset_files(opts, configs):
    for p in configs['paths']:
        log.notice('Examining: %s' % (os.path.relpath(p)))
    for r in strip_common_prefix(get_root_bset_files(opts, configs)):
        log.notice(' %s' % (r))


def list_bset_files(opts, configs):
    for p in configs['paths']:
        log.notice('Examining: %s' % (os.path.relpath(p)))
    for b in get_bset_files(configs):
        log.notice(' %s' % (b[:b.rfind('.')]))


def load_log(logfile):
    log.default = log.log(streams=[logfile])


def log_default(name):
    return 'rsb-log-%s-%s.txt' % (
        name, datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))


def load_options(argv, argopts, defaults='%{_sbdir}/defaults.mc', extras=[]):
    opts = options(argv, argopts, defaults, extras)
    opts.defaults['rtems_version'] = str(argopts.rtems_version)
    return opts
