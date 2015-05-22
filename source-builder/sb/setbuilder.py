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
# This code builds a package compiler tool suite given a tool set. A tool
# set lists the various tools. These are specific tool configurations.
#

import copy
import datetime
import glob
import operator
import os
import sys

try:
    import build
    import check
    import error
    import log
    import mailer
    import options
    import path
    import reports
    import sources
    import version
except KeyboardInterrupt:
    print 'abort: user terminated'
    sys.exit(1)
except:
    print 'error: unknown application load error'
    sys.exit(1)

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
        self.bset = bset
        _target = self.macros.expand('%{_target}')
        if len(_target):
            pkg_prefix = _target
        else:
            pkg_prefix = self.macros.expand('%{_host}')
        self.bset_pkg = '%s-%s-set' % (pkg_prefix, self.bset)
        self.mail_header = ''
        self.mail_report = ''
        self.build_failure = None

    def write_mail_header(self, text, prepend = False):
        if len(text) == 0 or text[-1] != '\n' or text[-1] != '\r':
            text += os.linesep
        if prepend:
            self.mail_header = text + self.mail_header
        else:
            self.mail_header += text

    def write_mail_report(self, text, prepend = False):
        if len(text) == 0 or text[-1] != '\n' or text[-1] != '\r':
            text += os.linesep
        if prepend:
            self.mail_report = text + self.mail_report
        else:
            self.mail_report += text

    def copy(self, src, dst):
        log.output('copy: %s => %s' % (path.host(src), path.host(dst)))
        if not self.opts.dry_run():
            path.copy_tree(src, dst)

    def report(self, _config, _build, opts, macros, format = None):
        if len(_build.main_package().name()) > 0 \
           and not _build.macros.get('%{_disable_reporting}') \
           and (not _build.opts.get_arg('--no-report') \
                or _build.opts.get_arg('--mail')):
            if format is None:
                format = _build.opts.get_arg('--report-format')
                if format is not None:
                    if len(format) != 2:
                        raise error.general('invalid report format option: %s' % ('='.join(format)))
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
            prefix = _build.macros.expand('%{_prefix}')
            name = _build.main_package().name() + ext
            log.notice('reporting: %s -> %s' % (_config, name))
            if not _build.opts.get_arg('--no-report'):
                outpath = path.host(path.join(buildroot, prefix, 'share', 'rtems', 'rsb'))
                if not _build.opts.dry_run():
                    outname = path.host(path.join(outpath, name))
                else:
                    outname = None
                r = reports.report(format, self.configs,
                                   copy.copy(opts), copy.copy(macros))
                r.introduction(_build.config.file_name())
                r.generate(_build.config.file_name())
                r.epilogue(_build.config.file_name())
                if not _build.opts.dry_run():
                    _build.mkdir(outpath)
                    r.write(outname)
                del r
            if _build.opts.get_arg('--mail'):
                r = reports.report('text', self.configs,
                                   copy.copy(opts), copy.copy(macros))
                r.introduction(_build.config.file_name())
                r.generate(_build.config.file_name())
                r.epilogue(_build.config.file_name())
                self.write_mail_report(r.out)
                del r

    def root_copy(self, src, dst):
        what = '%s -> %s' % \
            (os.path.relpath(path.host(src)), os.path.relpath(path.host(dst)))
        log.trace('_bset: %s: collecting: %s' % (self.bset, what))
        self.copy(src, dst)

    def install(self, name, buildroot, prefix):
        dst = prefix
        src = path.join(buildroot, prefix)
        log.notice('installing: %s -> %s' % (name, path.host(dst)))
        self.copy(src, dst)

    def canadian_cross(self, _build):
        # @fixme Switch to using a private macros map.
        macros_to_save = ['%{_prefix}',
                          '%{_tmproot}',
                          '%{buildroot}',
                          '%{_builddir}',
                          '%{_host}']
        macros_to_copy = [('%{_host}',     '%{_build}'),
                          ('%{_tmproot}',  '%{_tmpcxcroot}'),
                          ('%{buildroot}', '%{buildcxcroot}'),
                          ('%{_builddir}', '%{_buildcxcdir}')]
        orig_macros = {}
        for m in macros_to_save:
            orig_macros[m] = _build.config.macro(m)
        for m in macros_to_copy:
            _build.config.set_define(m[0], _build.config.macro(m[1]))
        _build.make()
        for m in macros_to_save:
            _build.config.set_define(m, orig_macros[m])
        if not _build.macros.get('%{_disable_collecting}'):
            self.root_copy(_build.config.expand('%{buildcxcroot}'),
                           _build.config.expand('%{_tmpcxcroot}'))

    def build_package(self, _config, _build):
        if not _build.disabled():
            if _build.canadian_cross():
                self.canadian_cross(_build)
            _build.make()
            if not _build.macros.get('%{_disable_collecting}'):
                self.root_copy(_build.config.expand('%{buildroot}'),
                               _build.config.expand('%{_tmproot}'))

    def bset_tar(self, _build):
        tardir = _build.config.expand('%{_tardir}')
        if self.opts.get_arg('--bset-tar-file') \
           and not _build.macros.get('%{_disable_packaging}'):
            path.mkdir(tardir)
            tar = path.join(tardir, _build.config.expand('%s.tar.bz2' % (self.bset_pkg)))
            log.notice('tarball: %s' % (os.path.relpath(path.host(tar))))
            if not self.opts.dry_run():
                tmproot = _build.config.expand('%{_tmproot}')
                cmd = _build.config.expand("'cd " + tmproot + \
                                               " && %{__tar} -cf - . | %{__bzip2} > " + tar + "'")
                _build.run(cmd, shell_opts = '-c', cwd = tmproot)

    def parse(self, bset):

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
        except IOError, err:
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
                    self.bset_pkg = self.macros.expand(ls[1].strip())
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
            root, ext = path.splitext(exbset)
            if exbset.endswith('.bset'):
                bset = exbset
            else:
                bset = '%s.bset' % (exbset)
            configs = self.parse(bset)
        return configs

    def build(self, deps = None, nesting_count = 0):

        build_error = False

        nesting_count += 1

        log.trace('_bset: %s: make' % (self.bset))
        log.notice('Build Set: %s' % (self.bset))

        if self.opts.get_arg('--mail'):
            mail_report_subject = '%s %s' % (self.bset, self.macros.expand('%{_host}'))

        current_path = os.environ['PATH']

        start = datetime.datetime.now()

        mail_report = False
        have_errors = False

        try:
            configs = self.load()

            log.trace('_bset: %s: configs: %s'  % (self.bset, ','.join(configs)))

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
                        log.trace('_bset: == %2d %s' % (nesting_count + 1, '=' * 75))
                        bs = buildset(configs[s], self.configs, opts, macros)
                        bs.build(deps, nesting_count)
                        del bs
                    elif configs[s].endswith('.cfg'):
                        mail_report = self.opts.get_arg('--mail')
                        log.trace('_bset: -- %2d %s' % (nesting_count + 1, '-' * 75))
                        try:
                            b = build.build(configs[s], self.opts.get_arg('--pkg-tar-files'),
                                            opts, macros)
                        except:
                            build_error = True
                            raise
                        if b.macros.get('%{_disable_reporting}'):
                            mail_report = False
                        if deps is None:
                            self.build_package(configs[s], b)
                            self.report(configs[s], b,
                                        copy.copy(self.opts),
                                        copy.copy(self.macros))
                            # Always product an XML report.
                            self.report(configs[s], b,
                                        copy.copy(self.opts),
                                        copy.copy(self.macros),
                                        format = 'xml')
                            if s == len(configs) - 1 and not have_errors:
                                self.bset_tar(b)
                        else:
                            deps += b.config.includes()
                        builds += [b]
                    else:
                        raise error.general('invalid config type: %s' % (configs[s]))
                except error.general, gerr:
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
            if deps is None \
               and not self.opts.no_install() \
               and not have_errors:
                for b in builds:
                    if not b.canadian_cross() \
                       and not b.disabled() \
                       and not b.macros.get('%{_disable_installing}'):
                        self.install(b.name(),
                                     b.config.expand('%{buildroot}'),
                                     b.config.expand('%{_prefix}'))
            if deps is None and \
                    (not self.opts.no_clean() or self.opts.always_clean()):
                for b in builds:
                    if not b.disabled():
                        log.notice('cleaning: %s' % (b.name()))
                        b.cleanup()
            for b in builds:
                del b
        except error.general, gerr:
            if not build_error:
                log.stderr(str(gerr))
            raise
        except KeyboardInterrupt:
            mail_report = False
            raise
        except:
            self.build_failure = 'RSB general failure'
            raise
        finally:
            end = datetime.datetime.now()
            os.environ['PATH'] = current_path
            build_time = str(end - start)
            if mail_report:
                to_addr = self.opts.get_arg('--mail-to')
                if to_addr is not None:
                    to_addr = to_addr[1]
                else:
                    to_addr = self.macros.expand('%{_mail_tools_to}')
                log.notice('Mailing report: %s' % (to_addr))
                self.write_mail_header('Build Time %s' % (build_time), True)
                self.write_mail_header('')
                m = mailer.mail(self.opts)
                if self.build_failure is not None:
                    mail_report_subject = 'Build: FAILED %s (%s)' %\
                        (mail_report_subject, self.build_failure)
                    pass_fail = 'FAILED'
                else:
                    mail_report_subject = 'Build: PASSED %s' % (mail_report_subject)
                if not self.opts.dry_run():
                    m.send(to_addr, mail_report_subject,
                           self.mail_header + self.mail_report)
            log.notice('Build Set: Time %s' % (build_time))

def list_bset_cfg_files(opts, configs):
    if opts.get_arg('--list-configs') or opts.get_arg('--list-bsets'):
        if opts.get_arg('--list-configs'):
            ext = '.cfg'
        else:
            ext = '.bset'
        for p in configs['paths']:
            print 'Examining: %s' % (os.path.relpath(p))
        for c in configs['files']:
            if c.endswith(ext):
                print '    %s' % (c)
        return True
    return False

def run():
    import sys
    ec = 0
    setbuilder_error = False
    try:
        optargs = { '--list-configs':  'List available configurations',
                    '--list-bsets':    'List available build sets',
                    '--list-deps':     'List the dependent files.',
                    '--bset-tar-file': 'Create a build set tar file',
                    '--pkg-tar-files': 'Create package tar files',
                    '--no-report':     'Do not create a package report.',
                    '--report-format': 'The report format (text, html, asciidoc).' }
        mailer.append_options(optargs)
        opts = options.load(sys.argv, optargs)
        log.notice('RTEMS Source Builder - Set Builder, v%s' % (version.str()))
        opts.log_info()
        if not check.host_setup(opts):
            raise error.general('host build environment is not set up correctly')
        configs = build.get_configs(opts)
        if opts.get_arg('--list-deps'):
            deps = []
        else:
            deps = None
        if not list_bset_cfg_files(opts, configs):
            prefix = opts.defaults.expand('%{_prefix}')
            if not opts.dry_run() and \
               not opts.canadian_cross() and \
               not opts.no_install() and \
               not path.ispathwritable(prefix):
                raise error.general('prefix is not writable: %s' % (path.host(prefix)))
            for bset in opts.params():
                setbuilder_error = True
                b = buildset(bset, configs, opts)
                b.build(deps)
                b = None
                setbuilder_error = False
        if deps is not None:
            c = 0
            for d in sorted(set(deps)):
                c += 1
                print 'dep[%d]: %s' % (c, d)
    except error.general, gerr:
        if not setbuilder_error:
            log.stderr(str(gerr))
        log.stderr('Build FAILED')
        ec = 1
    except error.internal, ierr:
        if not setbuilder_error:
            log.stderr(str(ierr))
        log.stderr('Internal Build FAILED')
        ec = 1
    except error.exit, eerr:
        pass
    except KeyboardInterrupt:
        log.notice('abort: user terminated')
        ec = 1
    sys.exit(ec)

if __name__ == "__main__":
    run()
