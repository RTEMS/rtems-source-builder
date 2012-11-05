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
# This code builds a cross-gcc compiler tool suite given a tool set. A tool
# set lists the various tools. These are specific tool configurations.
#

import distutils.dir_util
import glob
import operator
import os

import build
import check
import defaults
import error
import log
import path

#
# Version of Source Builder Set Builder.
#
version = '0.1'

def _trace(opts, text):
    if opts.trace():
        print text

def _notice(opts, text):
    if not opts.quiet() and not log.default.has_stdout():
        print text
    log.output(text)
    log.flush()

class buildset:
    """Build a set builds a set of packages."""

    def __init__(self, bset, _defaults, opts):
        _trace(opts, '_bset:%s: init' % (bset))
        self.opts = opts
        self.defaults = _defaults
        self.bset = bset
        self.bset_pkg = '%s-%s-set' % (self.opts.expand('%{_target}', _defaults),
                                       self.bset)

    def _output(self, text):
        if not self.opts.quiet():
            log.output(text)

    def copy(self, src, dst):
        if os.path.isdir(path.host(src)):
            topdir = self.opts.expand('%{_topdir}', self.defaults)
            what = '%s -> %s' % \
                (path.host(src[len(topdir) + 1:]), path.host(dst[len(topdir) + 1:]))
            _notice(self.opts, 'installing: %s' % (what))
            if not self.opts.dry_run():
                try:
                    files = distutils.dir_util.copy_tree(path.host(src),
                                                         path.host(dst))
                    for f in files:
                        self._output(f)
                except IOError, err:
                    raise error.general('installing tree: %s: %s' % (what, str(err)))
                except distutils.errors.DistutilsFileError, err:
                    raise error.general('installing tree: %s' % (str(err)))

    def first_package(self, _build):
        tmproot = path.abspath(_build.config.expand('%{_tmproot}'))
        _build.rmdir(tmproot)
        _build.mkdir(tmproot)
        prefix = _build.config.expand('%{_prefix}')
        if prefix[0] == os.sep:
            prefix = prefix[1:]
        tmpprefix = path.join(tmproot, prefix)
        tmpbindir = path.join(tmpprefix, 'bin')
        # exporting to the environment
        os.environ['SB_TMPPREFIX'] = tmpprefix
        os.environ['SB_TMPBINDIR'] = tmpbindir
        os.environ['PATH'] = path.host(tmpbindir) + os.pathsep + os.environ['PATH']
        self._output('path: ' + os.environ['PATH'])
        # shell format
        return tmproot

    def every_package(self, _build, tmproot):
        self.copy(_build.config.abspath('%{buildroot}'), tmproot)

    def last_package(self, _build, tmproot):
        tar = path.join(_build.config.expand('%{_tardir}'),
                        _build.config.expand('%s.tar.bz2' % (self.bset_pkg)))
        _notice(self.opts, 'tarball: %s' % path.host(tar))
        if not self.opts.dry_run():
            cmd = _build.config.expand("'cd " + tmproot + \
                                           " && %{__tar} -cf - . | %{__bzip2} > " + tar + "'")
            _build.run(cmd, shell_opts = '-c', cwd = tmproot)

    def load(self):

        def _clean(line):
            line = line[0:-1]
            b = line.find('#')
            if b >= 0:
                line = line[1:b]
            return line.strip()

        exbset = self.opts.expand(self.bset, self.defaults)

        self.defaults['_bset'] = ('none', 'none', exbset)

        root, ext = path.splitext(exbset)

        if exbset.endswith('.cfg'):
            bsetcfg = exbset
        else:
            bsetcfg = '%s.cfg' % (exbset)

        bsetname = bsetcfg

        if not path.exists(bsetname):
            for cp in self.opts.expand('%{_configdir}', self.defaults).split(':'):
                configdir = path.abspath(cp)
                bsetname = path.join(configdir, bsetcfg)
                if path.exists(bsetname):
                    break
                bsetname = None
            if bsetname is None:
                raise error.general('no build set file found: %s' % (bsetcfg))
        try:
            if self.opts.trace():
                print '_bset:%s: open: %s' % (self.bset, bsetname)
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
                if self.opts.trace():
                    print '%03d: %s' % (lc, l)
                if ':' in l:
                    ls = l.split(':')
                    if ls[0].strip() == 'package':
                        self.bset_pkg = self.opts.expand(ls[1].strip(), self.defaults)
                        self.defaults['package'] = ('none', 'none', self.bset_pkg)
                elif l[0] == '%':
                    if l.startswith('%define'):
                        ls = l.split()
                        self.defaults[ls[1].strip()] = ('none', 'none', ls[2].strip())
                    else:
                        raise error.general('invalid directive in build set files: %s' % (l))
                else:
                    configs += [l.strip()]
        except:
            bset.close()
            raise

        bset.close()

        return configs

    def make(self):

        _trace(self.opts, '_bset:%s: make' % (self.bset))
        _notice(self.opts, 'bset: %s' % (self.bset))

        configs = self.load()

        _trace(self.opts, '_bset:%s: configs: %s'  % (self.bset, ','.join(configs)))

        current_path = os.environ['PATH']
        try:
            builds = []
            for s in range(0, len(configs)):
                b = build.build(configs[s], _defaults = self.defaults, opts = self.opts)
                if s == 0:
                    tmproot = self.first_package(b)
                b.make()
                self.every_package(b, tmproot)
                if s == len(configs) - 1:
                    self.last_package(b, tmproot)
                builds += [b]
            if not self.opts.no_clean():
                for b in builds:
                    _notice(self.opts, 'cleaning: %s' % (b.name()))
                    b.cleanup()
            for b in builds:
                del b
        except:
            os.environ['PATH'] = current_path
            raise
        os.environ['PATH'] = current_path

def run():
    import sys
    try:
        optargs = { '--list-configs': 'List available configurations' }
        opts, _defaults = defaults.load(sys.argv, optargs)
        log.default = log.log(opts.logfiles())
        _notice(opts, 'Source Builder - Set Builder, v%s' % (version))
        if not check.host_setup(opts, _defaults):
            if not opts.force():
                raise error.general('host build environment is not set up correctly (use --force to proceed)')
            _notice(opts, 'warning: forcing build with known host setup problems')
        if opts.get_arg('--list-configs'):
            build.list_configs(opts, _defaults)
        else:
            for bset in opts.params():
                c = buildset(bset, _defaults = _defaults, opts = opts)
                c.make()
                del c
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
    run()
