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
# Determine the defaults and load the specific file.
#

import glob
import pprint
import re
import os

import error
import execute
import path

basepath = 'sb'

#
# All paths in defaults must be Unix format. Do not store any Windows format
# paths in the defaults.
#
# Every entry must describe the type of checking a host must pass.
#

defaults = {
# Nothing
'nil':                 ('none', 'none', ''),

# Set to invalid values.
'_bset':               ('none',    'none', ''),
'name':                ('none',    'none', ''),
'version':             ('none',    'none', ''),
'release':             ('none',    'none', ''),

# GNU triples needed to build packages
'_host':               ('triplet', 'required', ''),
'_build':              ('triplet', 'required', '%{_host}'),
'_target':             ('none',    'optional', ''),

# Paths
'_host_platform':      ('none',    'none',     '%{_host_cpu}-%{_host_vendor}-%{_host_os}%{?_gnu}'),
'_build':              ('none',    'none',     '%{_host}'),
'_arch':               ('none',    'none',     '%{_host_arch}'),
'_sbdir':              ('none',    'none',     ''),
'_topdir':             ('dir',     'required',  path.shell(os.getcwd())),
'_configdir':          ('dir',     'optional', '%{_topdir}/config:%{_sbdir}/config'),
'_tardir':             ('dir',     'optional', '%{_topdir}/tar'),
'_sourcedir':          ('dir',     'optional', '%{_topdir}/sources'),
'_patchdir':           ('dir',     'optional', '%{_topdir}/patches:%{_sbdir}/patches'),
'_builddir':           ('dir',     'optional', '%{_topdir}/build/%{name}-%{version}-%{release}'),
'_docdir':             ('dir',     'none',     '%{_defaultdocdir}'),
'_tmppath':            ('dir',     'none',     '%{_topdir}/build/tmp'),
'_tmproot':            ('dir',     'none',     '%{_tmppath}/source-build-%(%{__id_u} -n)/%{_bset}'),
'buildroot:':          ('dir',     'none',     '%{_tmppath}/%{name}-root-%(%{__id_u} -n)'),
'_datadir':            ('dir',     'none',     '%{_prefix}/share'),
'_defaultdocdir':      ('dir',     'none',     '%{_prefix}/share/doc'),
'_exeext':             ('none',    'none',     ''),
'_exec_prefix':        ('dir',     'none',     '%{_prefix}'),
'_bindir':             ('dir',     'none',     '%{_exec_prefix}/bin'),
'_sbindir':            ('dir',     'none',     '%{_exec_prefix}/sbin'),
'_libexecdir':         ('dir',     'none',     '%{_exec_prefix}/libexec'),
'_datarootdir':        ('dir',     'none',     '%{_prefix}/share'),
'_datadir':            ('dir',     'none',     '%{_datarootdir}'),
'_sysconfdir':         ('dir',     'none',     '%{_prefix}/etc'),
'_sharedstatedir':     ('dir',     'none',     '%{_prefix}/com'),
'_localstatedir':      ('dir',     'none',     '%{prefix}/var'),
'_includedir':         ('dir',     'none',     '%{_prefix}/include'),
'_lib':                ('dir',     'none',     'lib'),
'_libdir':             ('dir',     'none',     '%{_exec_prefix}/%{_lib}'),
'_libexecdir':         ('dir',     'none',     '%{_exec_prefix}/libexec'),
'_mandir':             ('dir',     'none',     '%{_datarootdir}/man'),
'_infodir':            ('dir',     'none',     '%{_datarootdir}/info'),
'_localedir':          ('dir',     'none',     '%{_datarootdir}/locale'),
'_localedir':          ('dir',     'none',     '%{_datadir}/locale'),
'_localstatedir':      ('dir',     'none',     '%{_prefix}/var'),
'_prefix':             ('dir',     'none',     '%{_usr}'),
'_usr':                ('dir',     'none',     '/usr/local'),
'_usrsrc':             ('dir',     'none',     '%{_usr}/src'),
'_var':                ('dir',     'none',     '/usr/local/var'),
'_varrun':             ('dir',     'none',     '%{_var}/run'),

# Defaults, override in platform specific modules.
'___setup_shell':      ('exe',     'required', '/bin/sh'),
'__aclocal':           ('exe',     'optional', 'aclocal'),
'__ar':                ('exe',     'required', 'ar'),
'__arch_install_post': ('exe',     'none',     '%{nil}'),
'__as':                ('exe',     'required', 'as'),
'__autoconf':          ('exe',     'required', 'autoconf'),
'__autoheader':        ('exe',     'required', 'autoheader'),
'__automake':          ('exe',     'required', 'automake'),
'__awk':               ('exe',     'required', 'awk'),
'__bash':              ('exe',     'optional', '/bin/bash'),
'__bison':             ('exe',     'required', '/usr/bin/bison'),
'__bzip2':             ('exe',     'required', '/usr/bin/bzip2'),
'__cat':               ('exe',     'required', '/bin/cat'),
'__cc':                ('exe',     'required', '/usr/bin/gcc'),
'__chgrp':             ('exe',     'required', '/usr/bin/chgrp'),
'__chmod':             ('exe',     'required', '/bin/chmod'),
'__chown':             ('exe',     'required', '/usr/sbin/chown'),
'__cp':                ('exe',     'required', '/bin/cp'),
'__cpp':               ('exe',     'none',     '%{__cc} -E'),
'__cxx':               ('exe',     'required', '/usr/bin/g++'),
'__flex':              ('exe',     'required', '/usr/bin/flex'),
'__grep':              ('exe',     'required', '/usr/bin/grep'),
'__gzip':              ('exe',     'required', '/usr/bin/gzip'),
'__id':                ('exe',     'required', '/usr/bin/id'),
'__id_u':              ('exe',     'none',     '%{__id} -u'),
'__install':           ('exe',     'required', '/usr/bin/install'),
'__install_info':      ('exe',     'optional', '/usr/bin/install-info'),
'__ld':                ('exe',     'required', '/usr/bin/ld'),
'__ldconfig':          ('exe',     'required', '/sbin/ldconfig'),
'__ln_s':              ('exe',     'none',     'ln -s'),
'__make':              ('exe',     'required', 'make'),
'__makeinfo':          ('exe',     'required', '/usr/bin/makeinfo'),
'__mkdir':             ('exe',     'required', '/bin/mkdir'),
'__mkdir_p':           ('exe',     'none',     '/bin/mkdir -p'),
'__mv':                ('exe',     'required', '/bin/mv'),
'__nm':                ('exe',     'required', '/usr/bin/nm'),
'__objcopy':           ('exe',     'optional', '/usr/bin/objcopy'),
'__objdump':           ('exe',     'optional', '/usr/bin/objdump'),
'__patch':             ('exe',     'required', '/usr/bin/patch'),
'__perl':              ('exe',     'optional', 'perl'),
'__ranlib':            ('exe',     'required', 'ranlib'),
'__rm':                ('exe',     'required', '/bin/rm'),
'__sed':               ('exe',     'required', '/usr/bin/sed'),
'__setup_post':        ('exe',     'none',     '%{__chmod} -R a+rX,g-w,o-w .'),
'__sh':                ('exe',     'required', '/bin/sh'),
'__tar':               ('exe',     'required', '/usr/bin/tar'),
'__tar_extract':       ('exe',     'none',     '%{__tar} -xvvf'),
'__unzip':             ('exe',     'required', '/usr/bin/unzip'),
'__xz':                ('exe',     'required', '/usr/bin/xz'),

# Shell Build Settings.
'___build_args': ('none', 'none', '-e'),
'___build_cmd':  ('none', 'none', '%{?_sudo:%{_sudo} }%{?_remsh:%{_remsh} %{_remhost} }%{?_remsudo:%{_remsudo} }%{?_remchroot:%{_remchroot} %{_remroot} }%{___build_shell} %{___build_args}'),
'___build_post': ('none', 'none', 'exit 0'),

# Prebuild set up script.
'___build_pre': ('none', 'none', '''# ___build_pre in as set up in defaults.py
# Directories
SB_SOURCE_DIR="%{_sourcedir}"
SB_BUILD_DIR="%{_builddir}"
SB_OPT_FLAGS="%{?_tmproot:-I%{_tmproot}/%{_prefix}/include -L%{_tmproot}/%{_prefix}/lib} %{optflags}"
SB_ARCH="%{_arch}"
SB_OS="%{_os}"
export SB_SOURCE_DIR SB_BUILD_DIR SB_OPT_FLAGS SB_ARCH SB_OS
# Documentation
SB_DOC_DIR="%{_docdir}"
export SB_DOC_DIR
# Packages
SB_PACKAGE_NAME="%{name}"
SB_PACKAGE_VERSION="%{version}"
SB_PACKAGE_RELEASE="%{release}"
export SBPACKAGE_NAME SB_PACKAGE_VERSION SB_PACKAGE_RELEASE
# Build root directory
%{?buildroot:SB_BUILD_ROOT="%{buildroot}"}
export SB_BUILD_ROOT
# The compiler flags
%{?_targetcflags:CFLAGS_FOR_TARGET="%{_targetcflags}"}
%{?_targetcxxflags:CXXFLAGS_FOR_TARGET="%{_targetcxxflags}"}
export CFLAGS_FOR_TARGET
export CXXFLAGS_FOR_TARGET
# Default environment set up.
LANG=C
export LANG
unset DISPLAY || :
umask 022
cd "%{_builddir}"'''),
'___build_shell': ('none', 'none', '%{?_buildshell:%{_buildshell}}%{!?_buildshell:/bin/sh}'),
'___build_template': ('none', 'none', '''#!%{___build_shell}
%{___build_pre}
%{nil}'''),

# Configure command
'configure': ('none', 'none', '''
CFLAGS="${CFLAGS:-%optflags}" ; export CFLAGS ;
CXXFLAGS="${CXXFLAGS:-%optflags}" ; export CXXFLAGS ;
FFLAGS="${FFLAGS:-%optflags}" ; export FFLAGS ;
./configure --build=%{_build} --host=%{_host} \
      --target=%{_target_platform} \
      --program-prefix=%{?_program_prefix} \
      --prefix=%{_prefix} \
      --exec-prefix=%{_exec_prefix} \
      --bindir=%{_bindir} \
      --sbindir=%{_sbindir} \
      --sysconfdir=%{_sysconfdir} \
      --datadir=%{_datadir} \
      --includedir=%{_includedir} \
      --libdir=%{_libdir} \
      --libexecdir=%{_libexecdir} \
      --localstatedir=%{_localstatedir} \
      --sharedstatedir=%{_sharedstatedir} \
      --mandir=%{_mandir} \
      --infodir=%{_infodir}''')
}

class command_line:
    """Process the command line in a common way for all Tool Builder commands."""

    _defaults = { 'params'   : [],
                  'warn-all' : '0',
                  'quiet'    : '0',
                  'no-force' : '1',
                  'trace'    : '0',
                  'dry-run'  : '0',
                  'no-clean' : '0',
                  'no-smp'   : '0',
                  'rebuild'  : '0' }

    #
    # The define and if it is a path and needs conversion.
    #
    _long_opts = { '--prefix'         : ('_prefix', True),
                   '--prefixbase'     : ('_prefixbase', True),
                   '--topdir'         : ('_topdir', True),
                   '--configdir'      : ('_configdir', True),
                   '--builddir'       : ('_builddir', True),
                   '--sourcedir'      : ('_sourcedir', True),
                   '--tmppath'        : ('_tmppath', True),
                   '--log'            : ('_logfile', False),
                   '--url'            : ('_url_base', False),
                   '--targetcflags'   : ('_targetcflags', False),
                   '--targetcxxflags' : ('_targetcxxflags', False),
                   '--libstdcxxflags' : ('_libstdcxxflags', False) }

    _long_true_opts = { '--no-force' : '_force',
                        '--trace'    : '_trace',
                        '--dry-run'  : '_dry_run',
                        '--warn-all' : '_warn_all',
                        '--no-clean' : '_no_clean',
                        '--no-smp'   : '_no_smp',
                        '--rebuild'  : '_rebuild' }

    _target_triplets = { '--host'   : '_host',
                         '--build'  : '_build',
                         '--target' : '_target' }

    def _help(self):
        print '%s: [options] [args]' % (self.command_name)
        print 'Source Builder, an RTEMS Tools Project (c) 2012-2013 Chris Johns'
        print 'Options and arguments:'
        print '--no-force             : Do not create directories that are missing'
        print '--trace                : Trace the execution (not current used)'
        print '--dry-run              : Do everything but actually run the build'
        print '--warn-all             : Generate warnings'
        print '--no-clean             : Do not clean up the build tree'
        print '--no-smp               : Run with 1 job and not as many as CPUs'
        print '--rebuild              : Rebuild (not used)'
        print '--host                 : Set the host triplet'
        print '--build                : Set the build triplet'
        print '--target               : Set the target triplet'
        print '--prefix path          : Tools build prefix, ie where they are installed'
        print '--prefixbase path      : '
        print '--topdir path          : Top of the build tree, default is $PWD'
        print '--configdir path       : Path to the configuration directory, default: ./config'
        print '--builddir path        : Path to the build directory, default: ./build'
        print '--sourcedir path       : Path to the source directory, default: ./source'
        print '--tmppath path         : Path to the temp directory, default: ./tmp'
        print '--log file             : Log file where all build out is written too'
        print '--url url              : URL to look for source'
        print '--targetcflags flags   : List of C flags for the target code'
        print '--targetcxxflags flags : List of C++ flags for the target code'
        print '--libstdcxxflags flags : List of C++ flags to build the target libstdc++ code'
        print '--with-<label>         : Add the --with-<label> to the build'
        print '--without-<label>      : Add the --without-<label> to the build'
        if self.optargs:
            for a in self.optargs:
                print '%-22s : %s' % (a, self.optargs[a])
        raise error.exit()

    def __init__(self, argv, optargs):
        self.command_path = path.dirname(argv[0])
        if len(self.command_path) == 0:
            self.command_path = '.'
        self.command_name = path.basename(argv[0])
        self.args = argv[1:]
        self.optargs = optargs
        self.defaults = {}
        for to in command_line._long_true_opts:
            self.defaults[command_line._long_true_opts[to]] = ('none', 'none', '0')
        self.defaults['_sbdir'] = ('dir', 'required', path.shell(self.command_path))
        self._process()

    def __str__(self):
        def _dict(dd):
            s = ''
            ddl = dd.keys()
            ddl.sort()
            for d in ddl:
                s += '  ' + d + ': ' + str(dd[d]) + '\n'
            return s

        s = 'command: ' + self.command() + \
            '\nargs: ' + str(self.args) + \
            '\nopts:\n' + _dict(self.opts)

        return s

    def _process(self):

        def _process_lopt(opt, arg, long_opts, args, values = False):
            for lo in long_opts:
                if values and opt.startswith(lo):
                    equals = opt.find('=')
                    if equals < 0:
                        if arg == len(args) - 1:
                            raise error.general('missing option value: ' + lo)
                        arg += 1
                        value = args[arg]
                    else:
                        value = opt[equals + 1:]
                    if type(long_opts[lo]) is tuple:
                        if long_opts[lo][1]:
                            value = path.shell(value)
                        macro = long_opts[lo][0]
                    else:
                        macro = long_opts[lo]
                    return lo, macro, value, arg
                elif opt == lo:
                    return lo, long_opts[lo], True, arg
            return None, None, None, arg

        self.opts = command_line._defaults
        i = 0
        while i < len(self.args):
            a = self.args[i]
            if a.startswith('-'):
                if a.startswith('--'):
                    if a.startswith('--warn-all'):
                        self.opts['warn-all'] = True
                    elif a == '--help':
                        self._help()
                    else:
                        lo, macro, value, i = _process_lopt(a, i,
                                                            command_line._long_true_opts,
                                                            self.args)
                        if lo:
                            self.defaults[macro] = ('none', 'none', '1')
                            self.opts[lo[2:]] = '1'
                        else:
                            lo, macro, value, i = _process_lopt(a, i,
                                                                command_line._long_opts,
                                                                self.args, True)
                            if lo:
                                self.defaults[macro] = ('none', 'none', value)
                                self.opts[lo[2:]] = value
                            else:
                                #
                                # The target triplet is 'cpu-vendor-os'.
                                #
                                lo, macro, value, i = _process_lopt(a, i,
                                                                    command_line._target_triplets,
                                                                    self.args, True)
                                if lo:
                                    #
                                    # This is a target triplet. Run it past config.sub to make
                                    # make sure it is ok.
                                    #
                                    e = execute.capture_execution()
                                    config_sub = path.join(self.command_path,
                                                           basepath, 'config.sub')
                                    exit_code, proc, output = e.shell(config_sub + ' ' + value)
                                    if exit_code == 0:
                                        value = output
                                    self.defaults[macro] = ('triplet', 'none', value)
                                    self.opts[lo[2:]] = value
                                    _arch = macro + '_cpu'
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
                                    self.defaults[_arch] = ('none', 'none', _arch_value)
                                    self.defaults[_vendor] = ('none', 'none', _vendor_value)
                                    self.defaults[_os] = ('none', 'none', _os_value)
                                if not lo and a not in self.optargs:
                                    raise error.general('invalid argument (try --help): %s' % (a))
                else:
                    if a == '-f':
                        self.opts['force'] = '1'
                    elif a == '-n':
                        self.opts['dry-run'] = '1'
                    elif a == '-q':
                        self.opts['quiet'] = '1'
                    elif a == '-?':
                        self._help()
                    else:
                        raise error.general('invalid argument (try --help): %s' % (a))
            else:
                self.opts['params'].append(a)
            i += 1

    def _post_process(self, _defaults):
        if self.no_smp():
            _defaults['_smp_mflags'] = ('none', 'none', _defaults['nil'][2])
        if _defaults['_host'][2] == _defaults['nil'][2]:
            raise error.general('host not set')
        return _defaults

    def expand(self, s, _defaults):
        """Simple basic expander of config file macros."""
        mf = re.compile(r'%{[^}]+}')
        expanded = True
        while expanded:
            expanded = False
            for m in mf.findall(s):
                name = m[2:-1]
                if name in _defaults:
                    s = s.replace(m, _defaults[name][2])
                    expanded = True
                else:
                    raise error.general('cannot process default macro: ' + m)
        return s

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

    def no_clean(self):
        return self.opts['no-clean'] != '0'

    def no_smp(self):
        return self.opts['no-smp'] != '0'

    def rebuild(self):
        return self.opts['rebuild'] != '0'

    def params(self):
        return self.opts['params']

    def get_arg(self, arg):
        if not arg in self.optargs:
            raise error.internal('bad arg: %s' % (arg))
        for a in self.args:
            if a.startswith(arg):
                return a
        return None

    def get_config_files(self, config):
        #
        # Convert to shell paths and return shell paths.
        #
        # @fixme should this use a passed in set of defaults and not
        #        not the initial set of values ?
        #
        config = path.shell(config)
        if '*' in config or '?' in config:
            print config
            configdir = path.dirname(config)
            configbase = path.basename(config)
            if len(configbase) == 0:
                configbase = '*'
            if not configbase.endswith('.cfg'):
                configbase = configbase + '.cfg'
            if len(configdir) == 0:
                configdir = self.expand(defaults['_configdir'][2], defaults)
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
        if 'log' in self.opts:
            return self.opts['log'].split(',')
        return ['stdout']

    def urls(self):
        if 'url' in self.opts:
            return self.opts['url'].split(',')
        return None

    def prefixbase(self):
        if 'prefixbase' in self.opts:
            return self.opts['prefixbase']
        return None

def load(args, optargs = None):
    """
    Copy the defaults, get the host specific values and merge them overriding
    any matching defaults, then create an options object to handle the command
    line merging in any command line overrides. Finally post process the
    command line.
    """
    d = defaults
    overrides = None
    if os.name == 'nt':
        import windows
        overrides = windows.load()
    else:
        uname = os.uname()
        try:
            if uname[0] == 'Darwin':
                import darwin
                overrides = darwin.load()
            elif uname[0] == 'FreeBSD':
                import freebsd
                overrides = freebsd.load()
            elif uname[0] == 'Linux':
                import linux
                overrides = linux.load()
        except:
            pass
    if overrides is None:
        raise error.general('no hosts defaults found; please add')
    for k in overrides:
        d[k] = overrides[k]
    o = command_line(args, optargs)
    for k in o.defaults:
        d[k] = o.defaults[k]
    d = o._post_process(d)
    return o, d

if __name__ == '__main__':
    import sys
    try:
        _opts, _defaults = load(args = sys.argv)
        print _opts
        pprint.pprint(_defaults)
    except error.general, gerr:
        print gerr
        sys.exit(1)
    except error.internal, ierr:
        print ierr
        sys.exit(1)
    sys.exit(0)
