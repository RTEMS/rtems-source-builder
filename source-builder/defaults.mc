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
# All paths in defaults must be Unix format. Do not store any Windows format
# paths in the defaults.
#
# Every entry must describe the type of checking a host must pass.
#
# Records:
#  key: type, attribute, value
#   type     : none, dir, exe, triplet
#   attribute: none, required, optional
#   value    : 'single line', '''multi line'''
#

#
# Global defaults
#
[global]

# Nothing
nil:                 none,    none,     ''

# Set to invalid values.
_bset:               none,    none,     ''
_bset_tmp:           none,    none,     ''
name:                none,    none,     ''
version:             none,    none,     ''
release:             none,    none,     ''
buildname:           none,    none,     '%{name}'

# The default is not released.
rsb_released:        none,    none,     '0'
rsb_version:         none,    none,     'no-version'

# GNU triples needed to build packages
_host:               triplet, required, ''
_build:              triplet, required, ''
_target:             none,    optional, ''

# RTEMS release URL
rtems_release_url:   none,    none,     'https://ftp.rtems.org/pub/rtems/releases/%{rtems_version}'

# The user
_uid:                none,    convert,  '%(%{__id_u})'

# Default flags that can be overridded to supply specific host or build
# flags and include paths to the tools. The host is the final platform
# the tools will run on and build is the host building the tools.
host_cflags:         none,    convert,  '-O2 -g -pipe'
host_cxxflags:       none,    convert,  '-O2 -g -pipe'
host_ldflags:        none,    convert,  ''
host_includes:       none,    convert,  ''
host_libs:           none,    convert,  ''
build_cflags:        none,    convert,  '-O2 -g -pipe'
build_cxxflags:      none,    convert,  '-O2 -g -pipe'
build_ldflags:       none,    convert,  ''
build_includes:      none,    convert,  ''
build_libs:          none,    convert,  ''

#
# Build and staging paths.
#
buildroot:           dir,     none,     '%{_tmppath}/%{buildname}-%{_uid}'
buildcxcroot:        dir,     none,     '%{_tmppath}/%{buildname}-%{_uid}-cxc'
buildxcroot:         dir,     none,     '%{_tmppath}/%{buildname}-%{_uid}-xx'
stagingroot:         dir,     none,     '%{_tmppath}/sb-%{_uid}-staging'

#
# Install mode can be installing or staging. Defaults to installing.
#
install_mode:        none,    none,     'installing'

# Extra path a platform can override.
_extra_path:         none,    none,     '%{_sbdir}'
_ld_library_path:    none,    none,     'LD_LIBRARY_PATH'

# Paths
_host_platform:      none,    none,     '%{_host_cpu}-%{_host_vendor}-%{_host_os}%{?_gnu}'
_host_cc:            none,    none,     'gcc'
_host_cxx:           none,    none,     'g++'
_arch:               none,    none,     '%{_host_arch}'
_topdir:             dir,     required, '%{_cwd}'
_configdir:          dir,     optional, '%{_topdir}/config:%{_sbdir}/config:%{_sbtop}/bare/config'
_tardir:             dir,     optional, '%{_topdir}/tar'
_sourcedir:          dir,     optional, '%{_topdir}/sources'
_patchdir:           dir,     optional, '%{_topdir}/patches:%{_sbdir}/patches'
_builddir:           dir,     optional, '%{_topdir}/build/%{buildname}'
_buildcxcdir:        dir,     optional, '%{_topdir}/build/%{buildname}-cxc'
_buildxcdir:         dir,     optional, '%{_topdir}/build/%{buildname}-xc'
_docdir:             dir,     none,     '%{_defaultdocdir}'
_tmppath:            dir,     none,     '%{_topdir}/build/tmp'
_tmproot:            dir,     none,     '%{_tmppath}/sb-%{_uid}/%{_bset_tmp}'
_tmpcxcroot:         dir,     none,     '%{_tmppath}/sb-%{_uid}-cxc/%{_bset_tmp}'
_datadir:            dir,     none,     '%{_prefix}/share'
_defaultdocdir:      dir,     none,     '%{_prefix}/share/doc'
_dry_run:            none,    none,     '0'
_exeext:             none,    none,     ''
_exec_prefix:        dir,     none,     '%{_prefix}'
_bindir:             dir,     none,     '%{_exec_prefix}/bin'
_sbindir:            dir,     none,     '%{_exec_prefix}/sbin'
_libexecdir:         dir,     none,     '%{_exec_prefix}/libexec'
_datarootdir:        dir,     none,     '%{_prefix}/share'
_datadir:            dir,     none,     '%{_datarootdir}'
_sysconfdir:         dir,     none,     '%{_prefix}/etc'
_sharedstatedir:     dir,     none,     '%{_prefix}/com'
_localstatedir:      dir,     none,     '%{prefix}/var'
_includedir:         dir,     none,     '%{_prefix}/include'
_lib:                dir,     none,     'lib'
_libdir:             dir,     none,     '%{_exec_prefix}/%{_lib}'
_libexecdir:         dir,     none,     '%{_exec_prefix}/libexec'
_mandir:             dir,     none,     '%{_datarootdir}/man'
_infodir:            dir,     none,     '%{_datarootdir}/info'
_localedir:          dir,     none,     '%{_datarootdir}/locale'
_localedir:          dir,     none,     '%{_datadir}/locale'
_localstatedir:      dir,     none,     '%{_prefix}/var'
_pathprepend:        none,    none,     ''
_pathpostpend:       none,    none,     ''
_prefix:             dir,     none,     '%{_usr}'
_usr:                dir,     none,     '/usr/local'
_usrsrc:             dir,     none,     '%{_usr}/src'
_var:                dir,     none,     '/usr/local/var'
_varrun:             dir,     none,     '%{_var}/run'

# Get source state
_rsb_getting_source: none,    none,     '0'

# Defaults, override in platform specific modules.
___setup_shell:      exe,     required, '/bin/sh'
__aclocal:           exe,     optional, 'aclocal'
__ar:                exe,     required, 'ar'
__arch_install_post: exe,     none,     '%{nil}'
__as:                exe,     required, 'as'
__autoconf:          exe,     optional, 'autoconf'
__autoheader:        exe,     optional, 'autoheader'
__automake:          exe,     optional, 'automake'
__autoreconf:        exe,     optional, 'autoreconf'
__awk:               exe,     required, 'awk'
__bash:              exe,     optional, '/bin/bash'
__bison:             exe,     required, '/usr/bin/bison'
__bzip2:             exe,     required, '/usr/bin/bzip2'
__cat:               exe,     required, '/bin/cat'
__cc:                exe,     required, 'gcc'
__chgrp:             exe,     required, '/usr/bin/chgrp'
__chmod:             exe,     required, '/bin/chmod'
__chown:             exe,     required, '/usr/sbin/chown'
__cmake:             exe,     optional, '/usr/bin/cmake'
__cp:                exe,     required, '/bin/cp'
__cpp:               exe,     none,     '%{__cc} -E'
__cvs:               exe,     optional, '/usr/bin/cvs'
__cvs_z:             none,    none,     '%{__cvs} -z 9'
__cxx:               exe,     required, 'g++'
__flex:              exe,     required, '/usr/bin/flex'
__git:               exe,     required, '/usr/bin/git'
__grep:              exe,     required, '/usr/bin/grep'
__gzip:              exe,     required, '/usr/bin/gzip'
__id:                exe,     required, '/usr/bin/id'
__id_u:              exe,     none,     '%{__id} -u'
__install:           exe,     required, '/usr/bin/install'
__install_info:      exe,     optional, '/usr/bin/install-info'
__ld:                exe,     required, '/usr/bin/ld'
__ldconfig:          exe,     required, '/sbin/ldconfig'
__ln_s:              exe,     none,     'ln -s'
__make:              exe,     required, 'make'
__makeinfo:          exe,     required, '/usr/bin/makeinfo'
__mkdir:             exe,     required, '/bin/mkdir'
__mkdir_p:           exe,     none,     '/bin/mkdir -p'
__mv:                exe,     required, '/bin/mv'
__nm:                exe,     required, '/usr/bin/nm'
__objcopy:           exe,     none,     '/usr/bin/objcopy'
__objdump:           exe,     none,     '/usr/bin/objdump'
__patch_bin:         exe,     required, '/usr/bin/patch'
__patch_opts:        none,    none,     '%{nil}'
__patch:             exe,     none,     '%{__patch_bin} %{__patch_opts}'
__perl:              exe,     optional, 'perl'
__ranlib:            exe,     required, 'ranlib'
__rm:                exe,     required, '/bin/rm'
__rmfile:            exe,     none,     '%{__rm} -f'
__rmdir:             exe,     none,     '%{__rm} -rf'
__sed:               exe,     required, '/usr/bin/sed'
__setup_post:        exe,     none,     '%{__chmod} -R a+rX,g-w,o-w .'
__sh:                exe,     required, '/bin/sh'
__tar:               exe,     required, '/usr/bin/tar'
__tar_extract:       exe,     none,     '%{__tar} -xvv'
__touch:             exe,     required, '/usr/bin/touch'
__unzip:             exe,     required, '/usr/bin/unzip'
__xz:                exe,     required, '/usr/bin/xz'

# Shell Build Settings.
___build_args:       none,    none,     '-e'
___build_cmd:        none,    none,     '%{?_sudo:%{_sudo} }%{?_remsh:%{_remsh} %{_remhost} }%{?_remsudo:%{_remsudo} }%{?_remchroot:%{_remchroot} %{_remroot} }%{___build_shell} %{___build_args}'
___build_post:       none,    none,     'exit 0'

# Prebuild set up script.
___build_pre:        none,    none,     '''# ___build_pre as set up in defaults.py
# Save the original path away.
export SB_ORIG_PATH=${PATH}
# Directories
%{?_prefix:SB_PREFIX="%{_prefix}"}
%{?_prefix:SB_PREFIX_CLEAN=$(echo "%{_prefix}" | %{__sed} -e 's/^\///')}
SB_SOURCE_DIR="%{_sourcedir}"
SB_BUILD_DIR="%{_builddir}"
# host == build, use build; host != build, host uses host and build uses build
SB_HOST_CPPFLAGS="%{host_includes}"
# Optionally do not add includes to c/cxx flags as newer configure's complain
SB_HOST_CFLAGS="%{host_cflags} %{!?host_cflags_no_includes %{host_includes}}"
SB_HOST_CXXFLAGS="%{host_cxxflags} %{!?host_cflags_no_includes %{host_includes}}"
SB_HOST_LDFLAGS="%{host_ldflags} %{?_tmproot:-L%{_tmproot}/${SB_PREFIX_CLEAN}/lib}"
SB_HOST_LIBS="%{host_libs}"
SB_BUILD_CFLAGS="%{build_cflags} %{?_tmproot:-I%{_tmproot}/${SB_PREFIX_CLEAN}/include}"
SB_BUILD_CXXFLAGS="%{build_cxxflags} %{?_tmproot:-I%{_tmproot}/${SB_PREFIX_CLEAN}/include}"
SB_BUILD_LDFLAGS="%{build_ldflags} %{?_tmproot:-L%{_tmproot}/${SB_PREFIX_CLEAN}/lib}"
SB_BUILD_LBS="%{build_libs}"
SB_CFLAGS="${SB_BUILD_CFLAGS} %{build_includes}"
SB_CXXFLAGS="${SB_BUILD_CXXFLAGS} %{build_includes}"
SB_ARCH="%{_arch}"
SB_OS="%{_os}"
export SB_SOURCE_DIR SB_BUILD_DIR SB_ARCH SB_OS
export SB_HOST_CPPFLAGS SB_HOST_CFLAGS SB_HOST_CXXFLAGS SB_HOST_LDFLAGS SB_HOST_LIBS
export SB_BUILD_CFLAGS SB_BUILD_CXXFLAGS SB_BUILD_LDFLAGS SB_BUILD_LIBS
export SB_CFLAGS SB_CXXFLAGS
# Documentation
SB_DOC_DIR="%{_docdir}"
export SB_DOC_DIR
# Packages
SB_PACKAGE_NAME="%{name}"
SB_PACKAGE_BUILDNAME="%{buildname}"
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
# Extra path support
%{?_extra_path:SB_EXTRAPATH="%{_extra_path}"}
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
if test -n "${SB_EXTRAPATH}" ; then
 PATH="${SB_EXTRAPATH}:$PATH"
fi
%{?_pathprepend:PATH="%{_pathprepend}:$PATH"}
%{?_pathpostpend:PATH="$PATH:%{_pathpostpend}"}
export PATH
# Default environment set up.
LANG=C
export LANG
unset DISPLAY || :
umask 022
cd "%{_builddir}"'''

___build_shell:      none,    none,     '%{?_buildshell:%{_buildshell}}%{!?_buildshell:/bin/sh}'

___build_template:   none,    none,     '''#!%{___build_shell}
%{___build_pre}
%{nil}'''

# Configure command
configure:           none,    none,     '''
CFLAGS="${CFLAGS:-${SB_CFLAGS}" ; export CFLAGS ;
CXXFLAGS="${CXXFLAGS:-${SB_CFLAGS}}" ; export CXXFLAGS ;
FFLAGS="${FFLAGS:-${SB_CFLAGS}}" ; export FFLAGS ;
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
      --infodir=%{_infodir}'''

# Build script support.
build_directory:     none,    none,     '''
if test "%{_build}" != "%{_host}" ; then
  # Cross-build (Xc) if no target or the host and target match.
  # Canadian-cross (Cxc) if build, host and target are all different.
  if test -z "%{_target}" -o "%{_host}" == "%{_target}" ; then
    build_dir="build-xc"
  else
    build_dir="build-cxc"
  fi
else
  build_dir="build"
fi'''

# Host/build flags.
host_build_flags:    none,    none,     '''
# Host and build flags, Cross build if host and build are different and
# Cxc build if target is deifned and also different.
# Note, gcc is not ready to be compiled with -std=gnu99 (this needs to be checked).
if test "%{_build}" != "%{_host}" ; then
  # Cross build
  CC=$(echo "%{_host}-%{_host_cc}" | sed -e 's,-std=gnu99 ,,')
  CXX=$(echo "%{_host}-%{_host_cxx}" | sed -e 's,-std=gnu99 ,,')
  CPPFLAGS="${SB_HOST_CPPFLAGS}"
  CFLAGS="${SB_HOST_CFLAGS}"
  CXXFLAGS="${SB_HOST_CXXFLAGS}"
  LDFLAGS="${SB_HOST_LDFLAGS}"
  LDLIBS="${SB_HOST_LIBS}"
  LIBS="${SB_HOST_LIBS}"
  # Host
  CPPFLAGS_FOR_HOST="${SB_HOST_CPPFLAGS}"
  CFLAGS_FOR_HOST="${SB_HOST_CFLAGS}"
  CXXFLAGS_FOR_HOST="${SB_HOST_CXXFLAGS}"
  LDFLAGS_FOR_HOST="${SB_HOST_LDFLAGS}"
  LDLIBS_FOR_HOST="${SB_HOST_LIBS}"
  LIBS_FOR_HOST="${SB_HOST_LIBS}"
  CXXFLAGS_FOR_HOST="${SB_HOST_CFLAGS}"
  CC_FOR_HOST=$(echo "%{_host_cc} ${SB_HOST_CFLAGS}" | sed -e 's,-std=gnu99 ,,')
  CXX_FOR_HOST=$(echo "%{_host_cxx} ${SB_HOST_CXXFLAGS}" | sed -e 's,-std=gnu99 ,,')
  # Build
  CFLAGS_FOR_BUILD="${SB_BUILD_CFLAGS}"
  CXXFLAGS_FOR_BUILD="${SB_BUILD_CXXFLAGS}"
  LDFLAGS_FOR_BUILD="${SB_BUILD_LDFLAGS}"
  LDLIBS_FOR_BUILD="${SB_BUILD_LIBS}"
  LIBS_FOR_BUILD="${SB_BUILD_LIBS}"
  CXXFLAGS_FOR_BUILD="${SB_BUILD_CFLAGS}"
  CC_FOR_BUILD=$(echo "%{__cc} ${SB_BUILD_CFLAGS}" | sed -e 's,-std=gnu99 ,,')
  CXX_FOR_BUILD=$(echo "%{__cxx} ${SB_BUILD_CXXFLAGS}" | sed -e 's,-std=gnu99 ,,')
else
  LDFLAGS="${SB_BUILD_LDFLAGS}"
  LDLIBS="${SB_BUILD_LIBS}"
  LIBS="${SB_BUILD_LIBS}"
  CC=$(echo "%{__cc} ${SB_BUILD_CFLAGS}" | sed -e 's,-std=gnu99 ,,')
  CXX=$(echo "%{__cxx} ${SB_BUILD_CXXFLAGS}" | sed -e 's,-std=gnu99 ,,')
  CC_FOR_BUILD=${CC}
  CXX_FOR_BUILD=${CXX}
fi
export CC CXX CPPFLAGS CFLAGS CXXFLAGS LDFLAGS LIBS LDLIBS
export CC_FOR_HOST CXX_FOR_HOST CPPFLAGS_FOR_HOST CFLAGS_FOR_HOST CXXFLAGS_FOR_HOST LDFLAGS_FOR_HOST LDLIBS_FOR_HOST LIBS_FOR_HOST
export CC_FOR_BUILD CXX_FOR_BUILD CFLAGS_FOR_BUILD CXXFLAGS_FOR_BUILD LDFLAGS_FOR_BUILD LDLIBS_FOR_BUILS LIBS_FOR_BUILS'''

# Build/build flags.
build_build_flags:    none,    none,     '''
# Build and build flags means force build == host
# gcc is not ready to be compiled with -std=gnu99
LDFLAGS="${SB_HOST_LDFLAGS}"
LIBS="${SB_HOST_LIBS}"
CC=$(echo "%{__cc} ${SB_CFLAGS}" | sed -e 's,-std=gnu99 ,,')
CXX=$(echo "%{__cxx} ${SB_CXXFLAGS}" | sed -e 's,-std=gnu99 ,,')
CC_FOR_BUILD=${CC}
CXX_FOR_BUILD=${CXX}
export CC CXX CC_FOR_BUILD CXX_FOR_BUILD CFLAGS LDFLAGS LIBS'''

# Default package settings
_forced_static:     none,         none, '-Xlinker -Bstatic ${LIBS_STATIC} -Xlinker -Bdynamic'
__xz:                exe,     required, '/usr/bin/xz'

# Mail Support
_mail_smtp_host:   none,         none, 'localhost'
_mail_tools_to:    none,         none, 'build@rtems.org'

# Newlib ICONV encodings
_newlib_iconv_encodings: none,      none, '''big5,cp775,cp850,cp852,cp855,\
cp866,euc_jp,euc_kr,euc_tw,iso_8859_1,iso_8859_10,iso_8859_11,\
iso_8859_13,iso_8859_14,iso_8859_15,iso_8859_2,iso_8859_3,\
iso_8859_4,iso_8859_5,iso_8859_6,iso_8859_7,iso_8859_8,iso_8859_9,\
iso_ir_111,koi8_r,koi8_ru,koi8_u,koi8_uni,ucs_2,ucs_2_internal,\
ucs_2be,ucs_2le,ucs_4,ucs_4_internal,ucs_4be,ucs_4le,us_ascii,\
utf_16,utf_16be,utf_16le,utf_8,win_1250,win_1251,win_1252,\
win_1253,win_1254,win_1255,win_1256,win_1257,win_1258'''

# Waf build root suffix, only use for win32 mingw ming32 OSs
#
# If on Windows we need to add the driver prefix to the built root as waf
# strips the driver prefix from the prefix path when joining it to the
# destdir path. Waf is correct in doing this and the RSB is design to match
# the configure behaviour which treats the whole path including the drive
# prefix as part of the path as just a path.
#
waf_build_root_suffix:   none,  none, ' %(echo %{_prefix} | cut -c 1-2)'

# Makefile.inc support for staging
rtems_makefile_inc:      none,  none, '''
export RTEMS_ROOT=%{rtems_bsp_rtems_root}
export PROJECT_RELEASE=%{rtems_bsp_prefix}
export RTEMS_MAKEFILE_PATH=%{rtems_bsp_prefix}
'''
