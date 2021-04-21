#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2016 Chris Johns (chrisj@rtems.org)
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
# Determine the defaults and load the specific file.
#

from __future__ import print_function

import datetime
import glob
import pprint
import re
import os
import string
import sys

from . import download
from . import error
from . import execute
from . import git
from . import log
from . import macros
from . import path
from . import sources
from . import version

basepath = 'sb'

#
# Save the host and POSIX state.
#
host_windows = False
host_posix = True

class command_line:
    """Process the command line in a common way for all Tool Builder commands."""

    def __init__(self, argv, optargs, _defaults, command_path):
        self._long_opts = {
            # key                       macro                handler            param  defs   init
            '--prefix'               : ('_prefix',           self._lo_path,     True,  None,  False),
            '--topdir'               : ('_topdir',           self._lo_path,     True,  None,  False),
            '--configdir'            : ('_configdir',        self._lo_path,     True,  None,  False),
            '--builddir'             : ('_builddir',         self._lo_path,     True,  None,  False),
            '--sourcedir'            : ('_sourcedir',        self._lo_path,     True,  None,  False),
            '--patchdir'             : ('_patchdir',         self._lo_path,     True,  None,  False),
            '--tmppath'              : ('_tmppath',          self._lo_path,     True,  None,  False),
            '--jobs'                 : ('_jobs',             self._lo_jobs,     True,  'max', True),
            '--log'                  : ('_logfile',          self._lo_string,   True,  None,  False),
            '--url'                  : ('_url_base',         self._lo_string,   True,  None,  False),
            '--no-download'          : ('_disable_download', self._lo_bool,     False, '0',   True),
            '--macros'               : ('_macros',           self._lo_string,   True,  None,  False),
            '--source-only-download' : ('_source_download',  self._lo_bool,     False, '0',   True),
            '--targetcflags'         : ('_targetcflags',     self._lo_string,   True,  None,  False),
            '--targetcxxflags'       : ('_targetcxxflags',   self._lo_string,   True,  None,  False),
            '--libstdcxxflags'       : ('_libstdcxxflags',   self._lo_string,   True,  None,  False),
            '--force'                : ('_force',            self._lo_bool,     False, '0',   True),
            '--quiet'                : ('_quiet',            self._lo_bool,     False, '0',   True),
            '--trace'                : ('_trace',            self._lo_bool,     False, '0',   True),
            '--dry-run'              : ('_dry_run',          self._lo_bool,     False, '0',   True),
            '--warn-all'             : ('_warn_all',         self._lo_bool,     False, '0',   True),
            '--no-clean'             : ('_no_clean',         self._lo_bool,     False, '0',   True),
            '--keep-going'           : ('_keep_going',       self._lo_bool,     False, '0',   True),
            '--always-clean'         : ('_always_clean',     self._lo_bool,     False, '0',   True),
            '--no-install'           : ('_no_install',       self._lo_bool,     False, '0',   True),
            '--regression'           : ('_regression',       self._lo_bool,     False, '0',   True),
            '--host'                 : ('_host',             self._lo_triplets, True,  None,  False),
            '--build'                : ('_build',            self._lo_triplets, True,  None,  False),
            '--target'               : ('_target',           self._lo_triplets, True,  None,  False),
            '--rtems-tools'          : ('_rtems_tools',      self._lo_string,   True,  None,  False),
            '--rtems-bsp'            : ('_rtems_bsp',        self._lo_string,   True,  None,  False),
            '--rtems-version'        : ('_rtems_version',    self._lo_string,   True,  None,  False),
            '--help'                 : (None,                self._lo_help,     False, None,  False)
            }

        self.command_path = command_path
        self.command_name = path.basename(argv[0])
        self.argv = argv
        self.args = argv[1:]
        self.optargs = optargs
        self.defaults = _defaults
        self.opts = { 'params' : [] }
        for lo in self._long_opts:
            self.opts[lo[2:]] = self._long_opts[lo][3]
            if self._long_opts[lo][4]:
                self.defaults[self._long_opts[lo][0]] = ('none',
                                                         'none',
                                                         self._long_opts[lo][3])

    def __str__(self):
        def _dict(dd):
            s = ''
            ddl = list(dd.keys())
            ddl.sort()
            for d in ddl:
                s += '  ' + d + ': ' + str(dd[d]) + '\n'
            return s

        s = 'command: ' + self.command() + \
            '\nargs: ' + str(self.args) + \
            '\nopts:\n' + _dict(self.opts)

        return s

    def _lo_string(self, opt, macro, value):
        if value is None:
            raise error.general('option requires a value: %s' % (opt))
        self.opts[opt[2:]] = value
        self.defaults[macro] = value

    def _lo_path(self, opt, macro, value):
        if value is None:
            raise error.general('option requires a path: %s' % (opt))
        value = path.abspath(value)
        self.opts[opt[2:]] = value
        self.defaults[macro] = value

    def _lo_jobs(self, opt, macro, value):
        if value is None:
            raise error.general('option requires a value: %s' % (opt))
        ok = False
        if value in ['max', 'none', 'half']:
            ok = True
        else:
            try:
                i = int(value)
                ok = True
            except:
                pass
            if not ok:
                try:
                    f = float(value)
                    ok = True
                except:
                    pass
        if not ok:
            raise error.general('invalid jobs option: %s' % (value))
        self.defaults[macro] = value
        self.opts[opt[2:]] = value

    def _lo_bool(self, opt, macro, value):
        if value is not None:
            raise error.general('option does not take a value: %s' % (opt))
        self.opts[opt[2:]] = '1'
        self.defaults[macro] = '1'

    def _lo_triplets(self, opt, macro, value):
        #
        # This is a target triplet. Run it past config.sub to make make sure it
        # is ok.  The target triplet is 'cpu-vendor-os'.
        #
        e = execute.capture_execution()
        config_sub = path.join(self.command_path,
                               basepath, 'config.sub')
        exit_code, proc, output = e.shell(config_sub + ' ' + value)
        if exit_code == 0:
            value = output
        self.defaults[macro] = ('triplet', 'none', value)
        self.opts[opt[2:]] = value
        _cpu = macro + '_cpu'
        _arch = macro + '_arch'
        _vendor = macro + '_vendor'
        _os = macro + '_os'
        _arch_value = ''
        _vendor_value = ''
        _os_value = ''
        dash = value.find('-')
        if dash >= 0:
            _arch_value = value[:dash]
            value = value[dash + 1:]
        dash = value.find('-')
        if dash >= 0:
            _vendor_value = value[:dash]
            value = value[dash + 1:]
        if len(value):
            _os_value = value
        self.defaults[_cpu]    = _arch_value
        self.defaults[_arch]   = _arch_value
        self.defaults[_vendor] = _vendor_value
        self.defaults[_os]     = _os_value

    def _lo_help(self, opt, macro, value):
        self.help()

    def help(self):
        print('%s: [options] [args]' % (self.command_name))
        print('RTEMS Source Builder, an RTEMS Tools Project (c) 2012-2019 Chris Johns')
        print('Options and arguments:')
        print('--force                : Force the build to proceed')
        print('--quiet                : Quiet output (not used)')
        print('--trace                : Trace the execution')
        print('--dry-run              : Do everything but actually run the build')
        print('--warn-all             : Generate warnings')
        print('--no-clean             : Do not clean up the build tree')
        print('--always-clean         : Always clean the build tree, even with an error')
        print('--keep-going           : Do not stop on an error.')
        print('--regression           : Set --no-install, --keep-going and --always-clean')
        print('--jobs                 : Run with specified number of jobs, default: num CPUs.')
        print('--host                 : Set the host triplet')
        print('--build                : Set the build triplet')
        print('--target               : Set the target triplet')
        print('--prefix path          : Tools build prefix, ie where they are installed')
        print('--topdir path          : Top of the build tree, default is $PWD')
        print('--configdir path       : Path to the configuration directory, default: ./config')
        print('--builddir path        : Path to the build directory, default: ./build')
        print('--sourcedir path       : Path to the source directory, default: ./source')
        print('--patchdir path        : Path to the patches directory, default: ./patches')
        print('--tmppath path         : Path to the temp directory, default: ./tmp')
        print('--macros file[,[file]  : Macro format files to load after the defaults')
        print('--log file             : Log file where all build out is written too')
        print('--url url[,url]        : URL to look for source')
        print('--no-download          : Disable the source downloader')
        print('--no-install           : Do not install the packages to the prefix')
        print('--targetcflags flags   : List of C flags for the target code')
        print('--targetcxxflags flags : List of C++ flags for the target code')
        print('--libstdcxxflags flags : List of C++ flags to build the target libstdc++ code')
        print('--source-only-download : Only download the source')
        print('--with-<label>         : Add the --with-<label> to the build')
        print('--without-<label>      : Add the --without-<label> to the build')
        print('--rtems-tools path     : Path to an install RTEMS tool set')
        print('--rtems-bsp arc/bsp    : Standard RTEMS architecure and BSP specifier')
        print('--rtems-version ver    : The RTEMS major/minor version string')
        if self.optargs:
            for a in self.optargs:
                print('%-22s : %s' % (a, self.optargs[a]))
        raise error.exit()

    def process(self):
        for a in self.args:
            if a == '-?' or a == '--help':
                self.help()
        arg = 0
        while arg < len(self.args):
            a = self.args[arg]
            if a.startswith('--'):
                los = a.split('=', 1)
                lo = los[0]
                if lo in self._long_opts:
                    long_opt = self._long_opts[lo]
                    if len(los) == 1:
                        if long_opt[2]:
                            if arg == len(self.args) - 1:
                                raise error.general('option requires a parameter: %s' % \
                                                    (lo))
                            arg += 1
                            value = self.args[arg]
                        else:
                            value = None
                    else:
                        value = '='.join(los[1:])
                    long_opt[1](lo, long_opt[0], value)
                else:
                    if a.startswith('--with'):
                        if len(los) != 1:
                            value = los[1]
                        else:
                            value = '1'
                        self.defaults[los[0][2:].replace('-', '_').lower()] = \
                            ('none', 'none', value)
                    else:
                        if lo not in self.optargs:
                            raise error.general('unknown option: %s' % (lo))
            else:
                if a.startswith('-'):
                    raise error.general('short options not supported; only "-?"')
                self.opts['params'].append(a)
            arg += 1

    def pre_process(self):
        arg = 0
        while arg < len(self.args):
            a = self.args[arg]
            if a == '--source-only-download':
                self.args += ['--dry-run',
                              '--with-download',
                              '--quiet',
                              '--without-log',
                              '--without-error-report']
            if a == '--dry-run':
                self.args += ['--without-error-report']
            arg += 1

    def post_process(self, logfile = True):
        # Handle the log first.
        logctrl = self.parse_args('--without-log')
        if logctrl is None:
            if logfile:
                logfiles = self.logfiles()
            else:
                logfiles = None
            log.default = log.log(streams = logfiles)
        if self.trace():
            log.tracing = True
        if self.quiet():
            log.quiet = True
        # Must have a host
        if self.defaults['_host'] == self.defaults['nil']:
            raise error.general('--host not set')
        # Must have a host
        if self.defaults['_build'] == self.defaults['nil']:
            raise error.general('--build not set')
        # Default prefix
        prefix = self.parse_args('--prefix')
        if prefix is None:
            value = path.join(self.defaults['_prefix'],
                              'rtems',
                              str(self.defaults['rtems_version']))
            self.opts['prefix'] = value
            self.defaults['_prefix'] = value
        # Manage the regression option
        if self.opts['regression'] != '0':
            self.opts['no-install'] = '1'
            self.defaults['_no_install'] = '1'
            self.opts['keep-going'] = '1'
            self.defaults['_keep_going'] = '1'
            self.opts['always-clean'] = '1'
            self.defaults['_always_clean'] = '1'
        # Handle the jobs for make
        if '_ncpus' not in self.defaults:
            raise error.general('host number of CPUs not set')
        ncpus = self.jobs(self.defaults['_ncpus'])
        if ncpus > 1:
            self.defaults['_smp_mflags'] = '-j %d' % (ncpus)
        else:
            self.defaults['_smp_mflags'] = self.defaults['nil']
        # Load user macro files
        um = self.user_macros()
        if um:
            checked = path.exists(um)
            if False in checked:
                raise error.general('macro file not found: %s' % \
                                    (um[checked.index(False)]))
            for m in um:
                self.defaults.load(m)
        # Check if the user has a private set of macros to load
        if 'RSB_MACROS' in os.environ:
            if path.exists(os.environ['RSB_MACROS']):
                self.defaults.load(os.environ['RSB_MACROS'])
        if 'HOME' in os.environ:
            rsb_macros = path.join(os.environ['HOME'], '.rsb_macros')
            if path.exists(rsb_macros):
                self.defaults.load(rsb_macros)

    def sb_released(self):
        if version.released():
            self.defaults['rsb_released'] = '1'
        self.defaults['rsb_version'] = version.string()

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

    def command(self):
        return path.join(self.command_path, self.command_name)

    def force(self):
        return self.opts['force'] != '0'

    def dry_run(self):
        return self.opts['dry-run'] != '0'

    def set_dry_run(self):
        self.opts['dry-run'] = '1'

    def quiet(self):
        return self.opts['quiet'] != '0'

    def trace(self):
        return self.opts['trace'] != '0'

    def warn_all(self):
        return self.opts['warn-all'] != '0'

    def keep_going(self):
        return self.opts['keep-going'] != '0'

    def no_clean(self):
        return self.opts['no-clean'] != '0'

    def always_clean(self):
        return self.opts['always-clean'] != '0'

    def no_install(self):
        return self.opts['no-install'] != '0'

    def canadian_cross(self):
        _host = self.defaults.expand('%{_host}')
        _build = self.defaults.expand('%{_build}')
        _target = self.defaults.expand('%{_target}')
        #
        # The removed fix has been put back. I suspect
        # this was done as a result of another issue that
        # has been fixed.
        #
        return len(_target) and len(_host) and len(_build) \
            and _host != _build and _host != _target

    def user_macros(self):
        #
        # Return something even if it does not exist.
        #
        if self.opts['macros'] is None:
            return None
        um = []
        configs = self.defaults.expand('%{_configdir}').split(':')
        for m in self.opts['macros'].split(','):
            if path.exists(m):
                um += [m]
            else:
                # Get the expanded config macros then check them.
                cm = path.expand(m, configs)
                ccm = path.exists(cm)
                if True in ccm:
                    # Pick the first found
                    um += [cm[ccm.index(True)]]
                else:
                    um += [m]
        return um if len(um) else None

    def jobs(self, cpus):
        cpus = int(cpus)
        if self.opts['jobs'] == 'none':
            cpus = 0
        elif self.opts['jobs'] == 'max':
            pass
        elif self.opts['jobs'] == 'half':
            cpus = cpus / 2
        else:
            ok = False
            try:
                i = int(self.opts['jobs'])
                cpus = i
                ok = True
            except:
                pass
            if not ok:
                try:
                    f = float(self.opts['jobs'])
                    cpus = f * cpus
                    ok = True
                except:
                    pass
                if not ok:
                    raise error.internal('bad jobs option: %s' % (self.opts['jobs']))
        if cpus <= 0:
            cpu = 1
        return cpus

    def params(self):
        return self.opts['params']

    def parse_args(self, arg, error = True, extra = True):
        for a in range(0, len(self.args)):
            if self.args[a].startswith(arg):
                lhs = None
                rhs = None
                if '=' in self.args[a]:
                    eqs = self.args[a].split('=', 1)
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

    def get_arg(self, arg):
        if self.optargs is None or arg not in self.optargs:
            return None
        return self.parse_args(arg)

    def find_arg(self, arg):
        if self.optargs is None or arg not in self.optargs:
            raise error.internal('bad arg: %s' % (arg))
        for a in self.args:
            sa = a.split('=')
            if sa[0].startswith(arg):
                return sa
        return None

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

    def get_config_files(self, config):
        #
        # Convert to shell paths and return shell paths.
        #
        # @fixme should this use a passed in set of defaults and not
        #        not the initial set of values ?
        #
        config = path.shell(config)
        if '*' in config or '?' in config:
            print(config)
            configdir = path.dirname(config)
            configbase = path.basename(config)
            if len(configbase) == 0:
                configbase = '*'
            if not configbase.endswith('.cfg'):
                configbase = configbase + '.cfg'
            if len(configdir) == 0:
                configdir = self.macros.expand(self.defaults['_configdir'])
            configs = []
            for cp in configdir.split(':'):
                hostconfigdir = path.host(cp)
                for f in glob.glob(os.path.join(hostconfigdir, configbase)):
                    configs += path.shell(f)
        else:
            configs = [config]
        return configs

    def config_files(self):
        configs = []
        for config in self.opts['params']:
            configs.extend(self.get_config_files(config))
        return configs

    def logfiles(self):
        if 'log' in self.opts and self.opts['log'] is not None:
            return self.opts['log'].split(',')
        return ['rsb-log-%s.txt' % (datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))]

    def urls(self):
        if self.opts['url'] is not None:
            return self.opts['url'].split(',')
        return None

    def download_disabled(self):
        return self.opts['no-download'] != '0'

    def disable_install(self):
        self.opts['no-install'] = '1'

    def info(self):
        # Filter potentially sensitive mail options out.
        filtered_args = [
            arg for arg in self.argv
            if all(
                smtp_opt not in arg
                for smtp_opt in [
                    '--smtp-host',
                    '--mail-to',
                    '--mail-from',
                    '--smtp-user',
                    '--smtp-password',
                    '--smtp-port'
                ]
            )
        ]
        s = ' Command Line: %s%s' % (' '.join(filtered_args), os.linesep)
        s += ' Python: %s' % (sys.version.replace('\n', ''))
        return s

    def log_info(self):
        log.output(self.info())

    def rtems_options(self):
        # Check for RTEMS specific helper options.
        rtems_tools = self.parse_args('--rtems-tools')
        if rtems_tools is not None:
            if self.get_arg('--with-tools') is not None:
                raise error.general('--rtems-tools and --with-tools cannot be used together')
            self.args.append('--with-tools=%s' % (rtems_tools[1]))
        rtems_version = self.parse_args('--rtems-version')
        if rtems_version is None:
            rtems_version = str(version.version())
        else:
            rtems_version = rtems_version[1]
        self.defaults['rtems_version'] = rtems_version
        rtems_arch_bsp = self.parse_args('--rtems-bsp')
        if rtems_arch_bsp is not None:
            if self.get_arg('--target') is not None:
                raise error.general('--rtems-bsp and --target cannot be used together')
            ab = rtems_arch_bsp[1].split('/')
            if len(ab) != 2:
                raise error.general('invalid --rtems-bsp option')
            self.args.append('--target=%s-rtems%s' % (ab[0], rtems_version))
            self.args.append('--with-rtems-bsp=%s' % (ab[1]))

def load(args, optargs = None, defaults = '%{_sbdir}/defaults.mc', logfile = True):
    """
    Copy the defaults, get the host specific values and merge them overriding
    any matching defaults, then create an options object to handle the command
    line merging in any command line overrides. Finally post process the
    command line.
    """

    global host_windows
    global host_posix

    #
    # The path to this command.
    #
    command_path = path.dirname(path.abspath(args[0]))
    if len(command_path) == 0:
        command_path = '.'

    #
    # The command line contains the base defaults object all build objects copy
    # and modify by loading a configuration.
    #
    o = command_line(args,
                     optargs,
                     macros.macros(name = defaults,
                                   sbdir = command_path),
                     command_path)

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
            raise error.general('failed to load %s host support: %s' % (uname[0], ge))
        except:
            raise error.general('failed to load %s host support' % (uname[0]))
    else:
        raise error.general('unsupported host type; please add')
    if overrides is None:
        raise error.general('no hosts defaults found; please add')
    for k in overrides:
        o.defaults[k] = overrides[k]

    o.sb_released()
    o.sb_git()
    o.rtems_options()
    o.pre_process()
    o.process()
    o.post_process(logfile)

    #
    # Load the release settings
    #
    def setting_error(msg):
        raise error.general(msg)
    hashes = version.load_release_settings('hashes')
    for hash in hashes:
        hs = hash[1].split()
        if len(hs) != 2:
            raise error.general('invalid release hash in VERSION')
        sources.hash((hs[0], hash[0], hs[1]), o.defaults, setting_error)
    release_path = version.load_release_setting('version', 'release_path',
                                                raw = True)
    if release_path is not None:
        try:
            release_path = ','.join([rp.strip() for rp in release_path.split(',')])
        except:
            raise error.general('invalid release path in VERSION')
        download.set_release_path(release_path, o.defaults)
    return o

def run(args):
    try:
        dpath = path.dirname(args[0])
        _opts = load(args = args,
                     defaults = path.join(dpath, 'defaults.mc'))
        log.notice('RTEMS Source Builder - Defaults, %s' % (version.string()))
        _opts.log_info()
        log.notice('Options:')
        log.notice(str(_opts))
        log.notice('Defaults:')
        log.notice(str(_opts.defaults))
        log.notice('with-opt1: %r' % (_opts.with_arg('opt1')))
        log.notice('without-opt2: %r' % (_opts.with_arg('opt2')))
    except error.general as gerr:
        print(gerr)
        sys.exit(1)
    except error.internal as ierr:
        print(ierr)
        sys.exit(1)
    except error.exit as eerr:
        pass
    except KeyboardInterrupt:
        _notice(opts, 'abort: user terminated')
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    run(sys.argv)
