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
# This code builds a package compiler tool suite given a tool set. A tool
# set lists the various tools. These are specific tool configurations.
#

from __future__ import print_function

import copy
import datetime
import glob
import operator
import os
import sys
import tarfile

import textwrap

try:
    from . import build
    from . import check
    from . import config
    from . import error
    from . import log
    from . import mailer
    from . import options
    from . import path
    from . import reports
    from . import shell
    from . import sources
    from . import version
except KeyboardInterrupt:
    print('abort: user terminated', file = sys.stderr)
    sys.exit(1)
except:
    raise

def macro_expand(macros, _str):
    cstr = None
    while cstr != _str:
        cstr = _str
        _str = macros.expand(_str)
        _str = shell.expand(macros, _str)
    return _str

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

class buildset:
    """Build a set builds a set of packages."""

    def __init__(self, bset, _configs, opts, macros = None):
        log.trace('_bset:   : %s: init' % (bset))
        self.configs = _configs
        self.opts = opts
        if macros is None:
            self.macros = copy.copy(opts.defaults)
        else:
            self.macros = copy.copy(macros)
        log.trace('_bset:   : %s: macro defaults' % (bset))
        log.trace(str(self.macros))
        self.bset = bset
        _target = macro_expand(self.macros, '%{_target}')
        if len(_target):
            pkg_prefix = _target
        else:
            pkg_prefix = macro_expand(self.macros, '%{_host}')
        self.bset_pkg = '%s-%s-set' % (pkg_prefix, self.bset)
        self.mail_header = ''
        self.mail_report = ''
        self.mail_report_0subject = ''
        self.build_failure = None

    def write_mail_header(self, text = '', prepend = False):
        if type(text) is list:
            text = os.linesep.join(text)
        text = text.replace('\r', '').replace('\n', os.linesep)
        if len(text) == 0 or text[-1] != os.linesep:
            text += os.linesep
        if prepend:
            self.mail_header = text + self.mail_header
        else:
            self.mail_header += text

    def get_mail_header(self):
        return self.mail_header

    def write_mail_report(self, text, prepend = False):
        if type(text) is list:
            text = os.linesep.join(text)
        text = text.replace('\r', '').replace('\n', os.linesep)
        if len(text) == 0 or text[-1] != os.linesep:
            text += os.linesep
        if prepend:
            self.mail_report = text + self.mail_report
        else:
            self.mail_report += text

    def get_mail_report(self):
        return self.mail_report

    def mail_single_report(self):
        return self.macros.get('%{mail_single_report}') != 0

    def mail_active(self, mail, nesting_count = 1):
        return mail is not None and not (self.mail_single_report() and nesting_count > 1)

    def mail_send(self, mail):
        if True: #not self.opts.dry_run():
            mail_subject = '%s on %s' % (self.bset, self.macros.expand('%{_host}'))
            if mail['failure'] is not None:
                mail_subject = 'FAILED %s (%s)' % (mail_subject, mail['failure'])
            else:
                mail_subject = 'PASSED %s' % (mail_subject)
            mail_subject = 'Build %s: %s' % (reports.platform(mode = 'system'),
                                             mail_subject)
            body = mail['log']
            body += (os.linesep * 2).join(mail['reports'])
            mail['mail'].send(mail['to'], mail_subject, body)

    def copy(self, src, dst):
        log.output('copy: %s => %s' % (path.host(src), path.host(dst)))
        if not self.opts.dry_run():
            path.copy_tree(src, dst)

    def report(self, _config, _build, opts, macros, format = None, mail = None):
        if len(_build.main_package().name()) > 0 \
           and not _build.macros.get('%{_disable_reporting}') \
           and (not _build.opts.get_arg('--no-report') \
                or _build.opts.get_arg('--mail')):
            if format is None:
                format = _build.opts.get_arg('--report-format')
                if format is not None:
                    if len(format) != 2:
                        raise error.general('invalid report format option: %s' % \
                                            ('='.join(format)))
                    format = format[1]
            if format is None:
                format = 'text'
            if format == 'text':
                ext = '.txt'
            elif format == 'asciidoc':
                ext = '.txt'
            elif format == 'html':
                ext = '.html'
            elif format == 'xml':
                ext = '.xml'
            elif format == 'ini':
                ext = '.ini'
            else:
                raise error.general('invalid report format: %s' % (format))
            buildroot = _build.config.abspath('%{buildroot}')
            prefix = macro_expand(_build.macros, '%{_prefix}')
            name = _build.main_package().name() + ext
            log.notice('reporting: %s -> %s' % (_config, name))
            if not _build.opts.get_arg('--no-report'):
                outpath = path.host(path.join(buildroot, prefix, 'share', 'rtems', 'rsb'))
                if not _build.opts.dry_run():
                    outname = path.host(path.join(outpath, name))
                else:
                    outname = None
                r = reports.report(format, False, self.configs,
                                   copy.copy(opts), copy.copy(macros))
                r.introduction(_build.config.file_name())
                r.generate(_build.config.file_name())
                r.epilogue(_build.config.file_name())
                if not _build.opts.dry_run():
                    _build.mkdir(outpath)
                    r.write(outname)
                del r
            if mail:
                r = reports.report('text', True, self.configs,
                                   copy.copy(opts), copy.copy(macros))
                r.introduction(_build.config.file_name())
                r.generate(_build.config.file_name())
                r.epilogue(_build.config.file_name())
                self.write_mail_report(r.get_output())
                del r

    def root_copy(self, src, dst):
        what = '%s -> %s' % \
            (os.path.relpath(path.host(src)), os.path.relpath(path.host(dst)))
        log.trace('_bset:   : %s: collecting: %s' % (self.bset, what))
        self.copy(src, dst)

    def install(self, mode, name, src, dst):
        log.trace('_bset:   : %s: copy %s -> %s' % (mode, src, dst))
        log.notice('%s: %s -> %s' % (mode, name, path.host(dst)))
        self.copy(src, dst)

    def install_mode(self):
        return macro_expand(self.macros, '%{install_mode}')

    def installing(self):
        return self.install_mode() == 'installing'

    def installable(self):
        return not self.opts.no_install() or self.staging()

    def staging(self):
        return not self.installing()

    def canadian_cross(self, _build):
        log.trace('_bset:   : Cxc for build machine: _build => _host')
        macros_to_copy = [('%{_host}',        '%{_build}'),
                          ('%{_host_alias}',  '%{_build_alias}'),
                          ('%{_host_arch}',   '%{_build_arch}'),
                          ('%{_host_cpu}',    '%{_build_cpu}'),
                          ('%{_host_os}',     '%{_build_os}'),
                          ('%{_host_vendor}', '%{_build_vendor}'),
                          ('%{_tmproot}',     '%{_tmpcxcroot}'),
                          ('%{buildroot}',    '%{buildcxcroot}'),
                          ('%{_builddir}',    '%{_buildcxcdir}')]
        cxc_macros = _build.copy_init_macros()
        for m in macros_to_copy:
            log.trace('_bset:   : Cxc: %s <= %s' % (m[0], cxc_macros[m[1]]))
            cxc_macros[m[0]] = cxc_macros[m[1]]
        _build.set_macros(cxc_macros)
        _build.reload()
        _build.make()
        if not _build.macros.get('%{_disable_collecting}'):
            self.root_copy(_build.config.expand('%{buildroot}'),
                           _build.config.expand('%{_tmproot}'))
        _build.set_macros(_build.copy_init_macros())
        _build.reload()

    def build_package(self, _config, _build):
        if not _build.disabled():
            if _build.canadian_cross():
                self.canadian_cross(_build)
            _build.make()
            if not _build.macros.get('%{_disable_collecting}'):
                self.root_copy(_build.config.expand('%{buildroot}'),
                               _build.config.expand('%{_tmproot}'))

    def bset_tar(self, stagingroot):
        if self.opts.get_arg('--bset-tar-file') or self.opts.canadian_cross():
            # Use a config to expand the macros because it supports all
            # expansions, ie %{_cwd}
            cfg = config.file(self.bset, self.opts, self.macros, load=False)
            prefix = cfg.expand('%{_prefix}')
            tardir = cfg.expand('%{_tardir}')
            path.mkdir(tardir)
            tarname = path.join(tardir,
                                path.basename('%s.tar.bz2' % (self.bset)))
            log.notice('tarfile: %s' % (os.path.relpath(path.host(tarname))))
            if not self.opts.dry_run():
                tar = None
                try:
                    tar = tarfile.open(tarname, 'w:bz2')
                    for filedir in sorted(path.listdir(stagingroot)):
                        src = path.join(stagingroot, filedir)
                        dst = path.join(prefix, filedir)
                        log.trace('tar: %s -> %s' % (src, dst))
                        tar.add(src, dst)
                except OSError as oe:
                    raise error.general('tarfile: %s: %s' % (self.bset, oe))
                finally:
                    if tar is not None:
                        tar.close()

    def parse(self, bset):

        def _clean(line):
            line = line[0:-1]
            b = line.find('#')
            if b >= 0:
                line = line[1:b]
            return line.strip()

        def _clean_and_pack(line, last_line):
            leading_ws = ' ' if len(line) > 0 and line[0].isspace() else ''
            line = _clean(line)
            if len(last_line) > 0:
                line = last_line + leading_ws + line
            return line

        bset = macro_expand(self.macros, bset)
        bsetname = bset

        if not path.exists(bsetname):
            for cp in macro_expand(self.macros, '%{_configdir}').split(':'):
                configdir = path.abspath(cp)
                bsetname = path.join(configdir, bset)
                if path.exists(bsetname):
                    break
                bsetname = None
            if bsetname is None:
                raise error.general('no build set file found: %s' % (bset))
        try:
            log.trace('_bset:   : %s: open: %s' % (self.bset, bsetname))
            bset = open(path.host(bsetname), 'r')
        except IOError as err:
            raise error.general('error opening bset file: %s' % (bsetname))

        configs = []

        try:
            lc = 0
            ll = ''
            for l in bset:
                lc += 1
                l = _clean_and_pack(l, ll)
                if len(l) == 0:
                    continue
                if l[-1] == '\\':
                    ll = l[0:-1]
                    continue
                ll = ''
                log.trace('_bset:   : %s: %03d: %s' % (self.bset, lc, l))
                ls = l.split()
                if ls[0][-1] == ':' and ls[0][:-1] == 'package':
                    self.bset_pkg = ls[1].strip()
                    self.macros['package'] = self.bset_pkg
                elif ls[0][0] == '%' and (len(ls[0]) > 1 and ls[0][1] != '{'):
                    def err(msg):
                        raise error.general('%s:%d: %s' % (self.bset, lc, msg))
                    if ls[0] == '%define' or ls[0] == '%defineifnot' :
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
                    l = macro_expand(self.macros, l.strip())
                    c = build.find_config(l, self.configs)
                    if c is None:
                        raise error.general('%s:%d: cannot find file: %s' % (self.bset,
                                                                             lc, l))
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
            exbset = macro_expand(self.macros, self.bset)
            self.macros['_bset'] = exbset
            bset_tmp = build.short_name(exbset)
            if bset_tmp.endswith('.bset'):
                bset_tmp = bset_tmp[:-5]
            self.macros['_bset_tmp'] = bset_tmp
            root, ext = path.splitext(exbset)
            if exbset.endswith('.bset'):
                bset = exbset
            else:
                bset = '%s.bset' % (exbset)
            configs = self.parse(bset)
        return configs

    def build(self, deps = None, nesting_count = 0, mail = None):

        build_error = False

        nesting_count += 1

        if self.mail_active(mail, nesting_count):
            mail['output'].clear()
            mail['log'] = ''
            mail['reports'] = []
            mail['failure'] = None

        log.trace('_bset: %2d: %s: make' % (nesting_count, self.bset))
        log.notice('Build Set: %s' % (self.bset))

        current_path = os.environ['PATH']

        start = datetime.datetime.now()

        mail_report = False
        have_errors = False
        interrupted = False

        #
        # If installing switch to staging. Not sure if this is still
        # needed.
        #
        if self.installing():
            self.macros['install_mode'] = 'staging'

        try:
            configs = self.load()

            log.trace('_bset: %2d: %s: configs: %s'  % (nesting_count,
                                                        self.bset, ', '.join(configs)))

            if nesting_count == 1:
                #
                # Prepend staging areas, bin directory to the
                # path. Lets the later package depend on the earlier
                # ones.
                #
                pathprepend = ['%{stagingroot}/bin'] + \
                    macro_expand(self.macros, '%{_pathprepend}').split(':')
                pathprepend = [pp for pp in pathprepend if len(pp)]
                if len(pathprepend) == 1:
                    self.macros['_pathprepend'] = pathprepend[0]
                else:
                    self.macros['_pathprepend'] = ':'.join(pathprepend)

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
                    if configs[s].endswith('.bset'):
                        log.trace('_bset: %2d: %s %s' % (nesting_count,
                                                         configs[s],
                                                         '=' * (74 - len(configs[s]))))
                        bs = buildset(configs[s], self.configs, opts, macros)
                        bs.build(deps, nesting_count, mail)
                        del bs
                    elif configs[s].endswith('.cfg'):
                        if mail:
                            mail_report = True
                        log.trace('_bset: %2d: %s %s' % (nesting_count,
                                                         configs[s],
                                                         '=' * (74 - len(configs[s]))))
                        try:
                            b = build.build(configs[s],
                                            self.opts.get_arg('--pkg-tar-files'),
                                            opts,
                                            macros)
                        except:
                            build_error = True
                            raise
                        if b.macros.get('%{_disable_reporting}'):
                            mail_report = False
                        if deps is None:
                            self.build_package(configs[s], b)
                            self.report(configs[s], b,
                                        copy.copy(self.opts),
                                        copy.copy(self.macros),
                                        mail = mail)
                            # Always produce an XML report.
                            self.report(configs[s], b,
                                        copy.copy(self.opts),
                                        copy.copy(self.macros),
                                        format = 'xml',
                                        mail = mail)
                        else:
                            deps += b.config.includes()
                        builds += [b]
                        #
                        # Dump post build macros.
                        #
                        log.trace('_bset:   : macros post-build')
                        log.trace(str(b.macros))
                    else:
                        raise error.general('invalid config type: %s' % (configs[s]))
                except error.general as gerr:
                    have_errors = True
                    if b is not None:
                        if self.build_failure is None:
                            self.build_failure = b.name()
                        self.write_mail_header('')
                        self.write_mail_header('= ' * 40)
                        self.write_mail_header('Build FAILED: %s' % (b.name()))
                        self.write_mail_header('- ' * 40)
                        self.write_mail_header(str(log.default))
                        self.write_mail_header('- ' * 40)
                        if self.opts.keep_going():
                            log.notice(str(gerr))
                            if self.opts.always_clean():
                                builds += [b]
                        else:
                            raise
                    else:
                        raise
            #
            # Installing or staging ...
            #
            log.trace('_bset: %2d: %s: deps:%r no-install:%r' % \
                      (nesting_count, self.install_mode(),
                       deps is None, self.opts.no_install()))
            log.trace('_bset: %2d: %s: builds: %s' % \
                      (nesting_count, self.install_mode(),
                       ', '.join([b.name() for b in builds])))
            if deps is None and not have_errors:
                for b in builds:
                    log.trace('_bset:   : %s: installable=%r build-installable=%r' % \
                              (self.install_mode(), self.installable(), b.installable()))
                    if b.installable():
                        prefix = b.config.expand('%{_prefix}')
                        buildroot = path.join(b.config.expand('%{buildroot}'), prefix)
                        if self.staging():
                            prefix = b.config.expand('%{stagingroot}')
                        if self.installable():
                            self.install(self.install_mode(), b.name(), buildroot, prefix)
            #
            # Sizes ...
            #
            if len(builds) > 1:
                size_build = 0
                size_installed = 0
                size_build_max = 0
                for b in builds:
                    s = b.get_build_size()
                    size_build += s
                    if s > size_build_max:
                        size_build_max = s
                    size_installed += b.get_installed_size()
                size_sources = 0
                for p in builds[0].config.expand('%{_sourcedir}').split(':'):
                    size_sources += path.get_size(p)
                size_patches = 0
                for p in builds[0].config.expand('%{_patchdir}').split(':'):
                    size_patches += path.get_size(p)
                size_total = size_sources + size_patches + size_installed
                build_max_size_human = build.humanize_number(size_build_max +
                                                             size_installed, 'B')
                build_total_size_human = build.humanize_number(size_total, 'B')
                build_sources_size_human = build.humanize_number(size_sources, 'B')
                build_patches_size_human = build.humanize_number(size_patches, 'B')
                build_installed_size_human = build.humanize_number(size_installed, 'B')
                build_size = 'usage: %s' % (build_max_size_human)
                build_size += ' total: %s' % (build_total_size_human)
                build_size += ' (sources: %s' % (build_sources_size_human)
                build_size += ', patches: %s' % (build_patches_size_human)
                build_size += ', installed %s)' % (build_installed_size_human)
                sizes_valid = True
            #
            # Cleaning ...
            #
            if deps is None and \
                    (not self.opts.no_clean() or self.opts.always_clean()):
                for b in builds:
                    if not b.disabled():
                        log.notice('cleaning: %s' % (b.name()))
                        b.cleanup()
            #
            # Log the build size message
            #
            if len(builds) > 1:
                log.notice('Build Sizes: %s' % (build_size))
            #
            # Clear out the builds ...
            #
            for b in builds:
                del b

            #
            # If builds have been staged install into the final prefix.
            #
            if not have_errors:
                stagingroot = macro_expand(self.macros, '%{stagingroot}')
                have_stagingroot = path.exists(stagingroot)
                do_install = not self.opts.no_install()
                if do_install:
                    log.trace('_bset: %2d: install staging, present: %s' % \
                              (nesting_count, have_stagingroot))
                if have_stagingroot:
                    prefix = macro_expand(self.macros, '%{_prefix}')
                    if do_install:
                        self.install(self.install_mode(), self.bset, stagingroot, prefix)
                    self.bset_tar(stagingroot)
                    staging_size = path.get_size(stagingroot)
                    if not self.opts.no_clean() or self.opts.always_clean():
                        log.notice('clean staging: %s' % (self.bset))
                        log.trace('removing: %s' % (stagingroot))
                        if not self.opts.dry_run():
                            if path.exists(stagingroot):
                                path.removeall(stagingroot)
                    log.notice('Staging Size: %s' % \
                               (build.humanize_number(staging_size, 'B')))
        except error.general as gerr:
            if not build_error:
                log.stderr(str(gerr))
            raise
        except KeyboardInterrupt:
            interrupted = True
            raise
        except:
            self.build_failure = 'RSB general failure'
            interrupted = True
            raise
        finally:
            end = datetime.datetime.now()
            os.environ['PATH'] = current_path
            build_time = str(end - start)
            if self.mail_single_report() and nesting_count == 1:
                mail_report = True
            if interrupted or self.macros.defined('mail_disable'):
                mail_report = False
            if mail_report and mail is not None:
                if self.installing():
                    self.write_mail_header('Build Time: %s' % (build_time), True)
                    self.write_mail_header('', True)
                    self.write_mail_header(mail['header'], True)
                    self.write_mail_header('')
                    log.notice('Mailing report: %s' % (mail['to']))
                    mail['log'] += self.get_mail_header()
                    if sizes_valid:
                        mail['log'] += 'Sizes' + os.linesep
                        mail['log'] += '=====' + os.linesep + os.linesep
                        mail['log'] += \
                            'Maximum build usage: ' + build_max_size_human + os.linesep
                        mail['log'] += \
                            'Total size: ' + build_total_size_human + os.linesep
                        mail['log'] += \
                            'Installed : ' + build_installed_size_human + os.linesep
                        mail['log'] += 'Sources: ' + build_sources_size_human + os.linesep
                        mail['log'] += 'Patches: ' + build_patches_size_human + os.linesep
                    mail['log'] += os.linesep
                    mail['log'] += 'Output' + os.linesep
                    mail['log'] += '======' + os.linesep + os.linesep
                    mail['log'] += os.linesep.join(mail['output'].get())
                    mail['log'] += os.linesep + os.linesep
                    mail['log'] += 'Report' + os.linesep
                    mail['log'] += '======' + os.linesep + os.linesep
                mail['reports'] += [self.get_mail_report()]
                if self.build_failure is not None:
                    mail['failure'] = self.build_failure
                if self.mail_active(mail, nesting_count):
                    try:
                        self.mail_send(mail)
                    except error.general as gerr:
                        log.notice('Mail Send Failure: %s' % (gerr))

            log.notice('Build Set: Time %s' % (build_time))

def list_bset_cfg_files(opts, configs):
    if opts.get_arg('--list-configs') or opts.get_arg('--list-bsets'):
        if opts.get_arg('--list-configs'):
            ext = '.cfg'
        else:
            ext = '.bset'
        for p in configs['paths']:
            print('Examining: %s' % (os.path.relpath(p)))
        for c in configs['files']:
            if c.endswith(ext):
                print('    %s' % (c))
        return True
    return False

def list_host(opts):
    if opts.get_arg('--list-host'):
        print('Host operating system information:')
        print('Operating system: %s' % macro_expand(opts.defaults, '%{_os}'))
        print('Number of processors: %s' % macro_expand(opts.defaults, '%{_ncpus}'))
        print('Build architecture: %s' % macro_expand(opts.defaults, '%{_host_arch}'))
        print('Host triplet: %s' % macro_expand(opts.defaults, '%{_host}'))
        return True
    return False

def run():
    import sys
    ec = 0
    setbuilder_error = False
    mail = None
    try:
        optargs = { '--list-configs':  'List available configurations',
                    '--list-bsets':    'List available build sets',
                    '--list-configs':  'List available configuration files.',
                    '--list-deps':     'List the dependent files.',
                    '--list-host':     'List host information and the host triplet.',
                    '--bset-tar-file': 'Create a build set tar file',
                    '--pkg-tar-files': 'Create package tar files',
                    '--no-report':     'Do not create a package report.',
                    '--report-format': 'The report format (text, html, asciidoc).' }
        mailer.append_options(optargs)
        opts = options.load(sys.argv, optargs)
        if opts.get_arg('--mail'):
            mail = { 'mail'   : mailer.mail(opts),
                     'output' : log_capture(),
                     'log'    : '',
                     'reports': [],
                     'failure': None }
            # Request this now to generate any errors.
            smtp_host = mail['mail'].smtp_host()
            to_addr = opts.get_arg('--mail-to')
            if to_addr is not None:
                mail['to'] = to_addr[1]
            else:
                mail['to'] = macro_expand(opts.defaults, '%{_mail_tools_to}')
            mail['from'] = mail['mail'].from_address()
        log.notice('RTEMS Source Builder - Set Builder, %s' % (version.string()))
        opts.log_info()
        if not check.host_setup(opts):
            raise error.general('host build environment is not set up correctly')
        if mail:
            mail['header'] = os.linesep.join(mail['output'].get()) + os.linesep
            mail['header'] += os.linesep
            mail['header'] += 'Host: '  + reports.platform('compact') + os.linesep
            indent = '       '
            for l in textwrap.wrap(reports.platform('extended'),
                                   width = 80 - len(indent)):
                mail['header'] += indent + l + os.linesep
        configs = build.get_configs(opts)
        if opts.get_arg('--list-deps'):
            deps = []
        else:
            deps = None

        if not list_bset_cfg_files(opts, configs) and not list_host(opts):
            prefix = macro_expand(opts.defaults, '%{_prefix}')
            if opts.canadian_cross():
                opts.disable_install()

            if not opts.dry_run() and \
               not opts.canadian_cross() and \
               not opts.no_install() and \
               not path.ispathwritable(prefix):
                raise error.general('prefix is not writable: %s' % (path.host(prefix)))

            for bset in opts.params():
                setbuilder_error = True
                b = buildset(bset, configs, opts)
                b.build(deps, mail = mail)
                b = None
                setbuilder_error = False

        if deps is not None:
            c = 0
            for d in sorted(set(deps)):
                c += 1
                print('dep[%d]: %s' % (c, d))
    except error.general as gerr:
        if not setbuilder_error:
            log.stderr(str(gerr))
        log.stderr('Build FAILED')
        ec = 1
    except error.internal as ierr:
        if not setbuilder_error:
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
