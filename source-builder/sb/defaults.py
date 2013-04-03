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
import git
import path
import sys

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
'_arch':               ('none',    'none',     '%{_host_arch}'),
'_sbdir':              ('none',    'none',     ''),
'_topdir':             ('dir',     'required',  path.shell(os.getcwd())),
'_configdir':          ('dir',     'optional', '%{_topdir}/config:%{_sbdir}/config'),
'_tardir':             ('dir',     'optional', '%{_topdir}/tar'),
'_sourcedir':          ('dir',     'optional', '%{_topdir}/sources'),
'_patchdir':           ('dir',     'optional', '%{_topdir}/patches:%{_sbdir}/patches'),
'_builddir':           ('dir',     'optional', '%{_topdir}/build/%{name}-%{version}-%{release}'),
'_buildcxcdir':        ('dir',     'optional', '%{_topdir}/build/%{name}-%{version}-%{release}-cxc'),
'_docdir':             ('dir',     'none',     '%{_defaultdocdir}'),
'_tmppath':            ('dir',     'none',     '%{_topdir}/build/tmp'),
'_tmproot':            ('dir',     'none',     '%{_tmppath}/source-build-%(%{__id_u} -n)/%{_bset}'),
'_tmpcxcroot':         ('dir',     'none',     '%{_tmppath}/source-build-%(%{__id_u} -n)-cxc/%{_bset}'),
'buildroot':           ('dir',     'none',     '%{_tmppath}/%{name}-root-%(%{__id_u} -n)'),
'buildcxcroot':        ('dir',     'none',     '%{_tmppath}/%{name}-root-%(%{__id_u} -n)-cxc'),
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
'__git':               ('exe',     'required', '/usr/bin/git'),
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
'__patch_bin':         ('exe',     'required', '/usr/bin/patch'),
'__patch_opts':        ('none',    'none',     '%{nil}'),
'__patch':             ('exe',     'none',     '%{__patch_bin} %{__patch_opts}'),
'__perl':              ('exe',     'optional', 'perl'),
'__ranlib':            ('exe',     'required', 'ranlib'),
'__rm':                ('exe',     'required', '/bin/rm'),
'__rmfile':            ('exe',     'none',     '%{__rm} -f'),
'__rmdir':             ('exe',     'none',     '%{__rm} -rf'),
'__sed':               ('exe',     'required', '/usr/bin/sed'),
'__setup_post':        ('exe',     'none',     '%{__chmod} -R a+rX,g-w,o-w .'),
'__sh':                ('exe',     'required', '/bin/sh'),
'__tar':               ('exe',     'required', '/usr/bin/tar'),
'__tar_extract':       ('exe',     'none',     '%{__tar} -xvvf'),
'__touch':             ('exe',     'required', '/usr/bin/touch'),
'__unzip':             ('exe',     'required', '/usr/bin/unzip'),
'__xz':                ('exe',     'required', '/usr/bin/xz'),

# Shell Build Settings.
'___build_args': ('none', 'none', '-e'),
'___build_cmd':  ('none', 'none', '%{?_sudo:%{_sudo} }%{?_remsh:%{_remsh} %{_remhost} }%{?_remsudo:%{_remsudo} }%{?_remchroot:%{_remchroot} %{_remroot} }%{___build_shell} %{___build_args}'),
'___build_post': ('none', 'none', 'exit 0'),

# Prebuild set up script.
'___build_pre': ('none', 'none', '''# ___build_pre in as set up in defaults.py
# Save the original path away.
export SB_ORIG_PATH=${PATH}
# Directories
%{?_prefix:SB_PREFIX="%{_prefix}"}
%{?_prefix:SB_PREFIX_CLEAN=$(echo "%{_prefix}" | %{__sed} -e \'s/^\///\')}
SB_SOURCE_DIR="%{_sourcedir}"
SB_BUILD_DIR="%{_builddir}"
SB_OPT_FLAGS="%{?_tmproot:-I%{_tmproot}/${SB_PREFIX_CLEAN}/include -L%{_tmproot}/${SB_PREFIX_CLEAN}/lib} %{optflags}"
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
export SB_PACKAGE_NAME SB_PACKAGE_VERSION SB_PACKAGE_RELEASE
# Build directories
export SB_PREFIX
%{?_builddir:SB_BUILD_DIR="%{_builddir}"}
%{?buildroot:SB_BUILD_ROOT="%{buildroot}"}
%{?buildroot:%{?_prefix:SB_BUILD_ROOT_BINDIR="%{buildroot}/${SB_PREFIX_CLEAN}/bin"}}
export SB_BUILD_ROOT SB_BUILD_DIR SB_BUILD_ROOT_BINDIR
%{?_buildcxcdir:SB_BUILD_CXC_DIR="%{_buildcxcdir}"}
%{?buildcxcroot:SB_BUILD_CXC_ROOT="%{buildcxcroot}"}
%{?buildcxcroot:%{?_prefix:SB_BUILD_CXC_ROOT_BINDIR="%{buildcxcroot}/${SB_PREFIX_CLEAN}/bin"}}
export SB_BUILD_CXC_ROOT SB_BUILD_CXC_DIR SB_BUILD_CXC_ROOT_BINDIR
%{?_tmproot:SB_TMPROOT="%{_tmproot}"}
%{?_tmproot:%{?_prefix:SB_TMPPREFIX="%{_tmproot}/${SB_PREFIX_CLEAN}"}}
%{?_tmproot:%{?_prefix:SB_TMPBINDIR="%{_tmproot}/${SB_PREFIX_CLEAN}/bin"}}
export SB_TMPROOT SB_TMPPREFIX SB_TMPBINDIR
%{?_tmpcxcroot:SB_TMPCXCROOT="%{_tmproot}"}
%{?_tmpcxcroot:%{?_prefix:SB_TMPCXCPREFIX="%{_tmpcxcroot}/${SB_PREFIX_CLEAN}"}}
%{?_tmpcxcroot:%{?_prefix:SB_TMPCXCBINDIR="%{_tmpcxcroot}/${SB_PREFIX_CLEAN}/bin"}}
export SB_TMPCXCROOT SB_TMPCXCPREFIX SB_TMPCXCBINDIR
# The compiler flags
%{?_targetcflags:CFLAGS_FOR_TARGET="%{_targetcflags}"}
%{?_targetcxxflags:CXXFLAGS_FOR_TARGET="%{_targetcxxflags}"}
export CFLAGS_FOR_TARGET
export CXXFLAGS_FOR_TARGET
# Set up the path. Put the CXC path first.
if test -n "${SB_TMPBINDIR}" ; then
 PATH="${SB_TMPBINDIR}:$PATH"
fi
if test -n "${SB_TMPCXCBINDIR}" ; then
 PATH="${SB_TMPCXCBINDIR}:$PATH"
fi
export PATH
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

    def __init__(self, argv, optargs):
        self._long_opts = {
            # key                 macro              handler            param  defs    init
            '--prefix'         : ('_prefix',         self._lo_path,     True,  None,  False),
            '--topdir'         : ('_topdir',         self._lo_path,     True,  None,  False),
            '--configdir'      : ('_configdir',      self._lo_path,     True,  None,  False),
            '--builddir'       : ('_builddir',       self._lo_path,     True,  None,  False),
            '--sourcedir'      : ('_sourcedir',      self._lo_path,     True,  None,  False),
            '--tmppath'        : ('_tmppath',        self._lo_path,     True,  None,  False),
            '--jobs'           : ('_jobs',           self._lo_jobs,     True,  'max', True),
            '--log'            : ('_logfile',        self._lo_string,   True,  None,  False),
            '--url'            : ('_url_base',       self._lo_string,   True,  None,  False),
            '--targetcflags'   : ('_targetcflags',   self._lo_string,   True,  None,  False),
            '--targetcxxflags' : ('_targetcxxflags', self._lo_string,   True,  None,  False),
            '--libstdcxxflags' : ('_libstdcxxflags', self._lo_string,   True,  None,  False),
            '--force'          : ('_force',          self._lo_bool,     False, '0',   True),
            '--quiet'          : ('_quiet',          self._lo_bool,     False, '0',   True),
            '--trace'          : ('_trace',          self._lo_bool,     False, '0',   True),
            '--dry-run'        : ('_dry_run',        self._lo_bool,     False, '0',   True),
            '--warn-all'       : ('_warn_all',       self._lo_bool,     False, '0',   True),
            '--no-clean'       : ('_no_clean',       self._lo_bool,     False, '0',   True),
            '--keep-going'     : ('_keep_going',     self._lo_bool,     False, '0',   True),
            '--always-clean'   : ('_always_clean',   self._lo_bool,     False, '0',   True),
            '--host'           : ('_host',           self._lo_triplets, True,  None,  False),
            '--build'          : ('_build',          self._lo_triplets, True,  None,  False),
            '--target'         : ('_target',         self._lo_triplets, True,  None,  False),
            '--help'           : (None,              self._lo_help,     False, None,  False)
            }

        self.command_path = path.dirname(argv[0])
        if len(self.command_path) == 0:
            self.command_path = '.'
        self.command_name = path.basename(argv[0])
        self.argv = argv
        self.args = argv[1:]
        self.optargs = optargs
        self.defaults = {}
        self.defaults['_sbdir'] = ('dir', 'required', path.shell(self.command_path))
        self.opts = { 'params' : [] }
        for lo in self._long_opts:
            self.opts[lo[2:]] = self._long_opts[lo][3]
            if self._long_opts[lo][4]:
                self.defaults[self._long_opts[lo][0]] = ('none', 'none', self._long_opts[lo][3])
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

    def _lo_string(self, opt, macro, value):
        if value is None:
            raise error.general('option requires a value: %s' % (opt))
        self.opts[opt[2:]] = value
        self.defaults[macro] = ('none', 'none', value)

    def _lo_path(self, opt, macro, value):
        if value is None:
            raise error.general('option requires a path: %s' % (opt))
        value = path.shell(value)
        self.opts[opt[2:]] = value
        self.defaults[macro] = ('none', 'none', value)

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
        self.defaults[macro] = ('none', 'none', value)
        self.opts[opt[2:]] = value

    def _lo_bool(self, opt, macro, value):
        if value is not None:
            raise error.general('option does not take a value: %s' % (opt))
        self.opts[opt[2:]] = '1'
        self.defaults[macro] = ('none', 'none', '1')

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
        self.defaults[_cpu] = ('none', 'none', _arch_value)
        self.defaults[_arch] = ('none', 'none', _arch_value)
        self.defaults[_vendor] = ('none', 'none', _vendor_value)
        self.defaults[_os] = ('none', 'none', _os_value)

    def _lo_help(self, opt, macro, value):
        self.help()

    def _help(self):
        print '%s: [options] [args]' % (self.command_name)
        print 'RTEMS Source Builder, an RTEMS Tools Project (c) 2012-2013 Chris Johns'
        print 'Options and arguments:'
        print '--force                : Force the build to proceed'
        print '--quiet                : Quiet output (not used)'
        print '--trace                : Trace the execution'
        print '--dry-run              : Do everything but actually run the build'
        print '--warn-all             : Generate warnings'
        print '--no-clean             : Do not clean up the build tree'
        print '--always-clean         : Always clean the build tree, even with an error'
        print '--jobs                 : Run with specified number of jobs, default: num CPUs.'
        print '--host                 : Set the host triplet'
        print '--build                : Set the build triplet'
        print '--target               : Set the target triplet'
        print '--prefix path          : Tools build prefix, ie where they are installed'
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

    def _process(self):
        arg = 0
        while arg < len(self.args):
            a = self.args[arg]
            if a == '-?':
                self._help()
            elif a.startswith('--'):
                los = a.split('=')
                lo = los[0]
                if lo in self._long_opts:
                    long_opt = self._long_opts[lo]
                    if len(los) == 1:
                        if long_opt[2]:
                            if arg == len(args) - 1:
                                raise error.general('option requires a parameter: %s' % (lo))
                            arg += 1
                            value = args[arg]
                        else:
                            value = None
                    else:
                        value = '='.join(los[1:])
                    long_opt[1](lo, long_opt[0], value)
            else:
                self.opts['params'].append(a)
            arg += 1

    def _post_process(self, _defaults):
        if _defaults['_host'][2] == _defaults['nil'][2]:
            raise error.general('host not set')
        if '_ncpus' not in _defaults:
            raise error.general('host number of CPUs not set')
        ncpus = self.jobs(_defaults['_ncpus'][2])
        if ncpus > 1:
            _defaults['_smp_mflags'] = ('none', 'none', '-j %d' % (ncpus))
        else:
            _defaults['_smp_mflags'] = ('none', 'none', _defaults['nil'][2])
        return _defaults

    def define(self, _defaults, key, value = '1'):
        _defaults[key] = ('none', 'none', value)

    def undefine(self, _defaults, key):
        if key in _defaults:
            del _defaults[key]

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
                    raise error.general('cannot expand default macro: %s in "%s"' %
                                        (m, s))
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

    def keep_going(self):
        return self.opts['keep-going'] != '0'

    def no_clean(self):
        return self.opts['no-clean'] != '0'

    def always_clean(self):
        return self.opts['always-clean'] != '0'

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

    def get_arg(self, arg):
        if not arg in self.optargs:
            raise error.internal('bad arg: %s' % (arg))
        for a in self.args:
            sa = a.split('=')
            if sa[0].startswith(arg):
                return sa
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
                configdir = self.expand(self.defaults['_configdir'][2], self.defaults)
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
        if self.opts['url'] is not None:
            return self.opts['url'].split(',')
        return None

def load(args, optargs = None):
    """
    Copy the defaults, get the host specific values and merge them overriding
    any matching defaults, then create an options object to handle the command
    line merging in any command line overrides. Finally post process the
    command line.
    """
    import copy
    d = copy.deepcopy(defaults)
    overrides = None
    if os.name == 'nt':
        import windows
        overrides = windows.load()
    elif os.name == 'posix':
        uname = os.uname()
        try:
            if uname[0].startswith('CYGWIN_NT'):
                import windows
                overrides = windows.load()
            elif uname[0] == 'Darwin':
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
    else:
        raise error.general('unsupported host type; please add')
    if overrides is None:
        raise error.general('no hosts defaults found; please add')
    for k in overrides:
        d[k] = overrides[k]
    o = command_line(args, optargs)
    for k in o.defaults:
        d[k] = o.defaults[k]
    d = o._post_process(d)
    repo = git.repo(o.expand('%{_sbdir}', d), o, d)
    if repo.valid():
        repo_valid = '1'
        repo_head = repo.head()
        repo_clean = repo.clean()
        repo_id = repo_head
        if not repo_clean:
            repo_id += '-modified'
    else:
        repo_valid = '0'
        repo_head = '%{nil}'
        repo_clean = '%{nil}'
        repo_id = 'no-repo'
    o.define(d, '_sbgit_valid', repo_valid)
    o.define(d, '_sbgit_head', repo_head)
    o.define(d, '_sbgit_clean', str(repo_clean))
    o.define(d, '_sbgit_id', repo_id)
    return o, d

def run(args):
    try:
        _opts, _defaults = load(args = args)
        print 'Options:'
        print _opts
        print 'Defaults:'
        for k in sorted(_defaults.keys()):
            d = _defaults[k]
            print '%-20s: %-8s %-10s' % (k, d[0], d[1]),
            indent = False
            if len(d[2]) == 0:
                print
            text_len = 80
            for l in d[2].split('\n'):
                while len(l):
                    if indent:
                        print '%20s  %8s %10s' % (' ', ' ', ' '),
                    print l[0:text_len],
                    l = l[text_len:]
                    if len(l):
                        print ' \\',
                    print
                    indent = True
    except error.general, gerr:
        print gerr
        sys.exit(1)
    except error.internal, ierr:
        print ierr
        sys.exit(1)
    except error.exit, eerr:
        pass
    except KeyboardInterrupt:
        _notice(opts, 'abort: user terminated')
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    run(sys.argv)
