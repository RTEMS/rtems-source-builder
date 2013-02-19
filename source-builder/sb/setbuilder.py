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

    def __init__(self, bset, _configs, _defaults, opts):
        _trace(opts, '_bset:%s: init' % (bset))
        self.opts = opts
        self.configs = _configs
        self.defaults = _defaults
        self.bset = bset
        self.bset_pkg = '%s-%s-set' % (self.opts.expand('%{_target}', _defaults),
                                       self.bset)

    def _output(self, text):
        if not self.opts.quiet():
            log.output(text)

    def _find_config(self, config):
        if config.endswith('.bset') or config.endswith('.cfg'):
            names = [config]
        else:
            names = ['%s.cfg' % (path.basename(config)),
                     '%s.bset' % (path.basename(config))]
        for c in self.configs['files']:
            if path.basename(c) in names:
                if path.dirname(config).endswith(path.dirname(config)):
                    return c
        return None

    def copy(self, src, dst):
        if os.path.isdir(path.host(src)):
            topdir = self.opts.expand('%{_topdir}', self.defaults)
            what = '%s -> %s' % \
                (path.host(src[len(topdir) + 1:]), path.host(dst[len(topdir) + 1:]))
            if self.opts.trace():
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

    def parse(self, bset):

        def _clean(line):
            line = line[0:-1]
            b = line.find('#')
            if b >= 0:
                line = line[1:b]
            return line.strip()

        bsetname = bset

        if not path.exists(bsetname):
            for cp in self.opts.expand('%{_configdir}', self.defaults).split(':'):
                configdir = path.abspath(cp)
                bsetname = path.join(configdir, bset)
                if path.exists(bsetname):
                    break
                bsetname = None
            if bsetname is None:
                raise error.general('no build set file found: %s' % (bset))
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
                        if len(ls) > 2:
                            self.defaults[ls[1].strip()] = ('none', 'none', ls[2].strip())
                        else:
                            self.defaults[ls[1].strip()] = ('none', 'none', '1')
                    elif l.startswith('%include'):
                        ls = l.split(' ')
                        configs += self.parse(ls[1].strip())
                    else:
                        raise error.general('invalid directive in build set files: %s' % (l))
                else:
                    l = l.strip()
                    c = self._find_config(l)
                    if c is None:
                        raise error.general('cannot find file: %s' % (l))
                    configs += [c]
        except:
            bset.close()
            raise

        bset.close()

        return configs

    def load(self):

        exbset = self.opts.expand(self.bset, self.defaults)

        self.defaults['_bset'] = ('none', 'none', exbset)

        root, ext = path.splitext(exbset)

        if exbset.endswith('.bset'):
            bset = exbset
        else:
            bset = '%s.bset' % (exbset)

        return self.parse(bset)

    def build(self):

        _trace(self.opts, '_bset:%s: make' % (self.bset))
        _notice(self.opts, 'Build Set: %s' % (self.bset))

        configs = self.load()

        _trace(self.opts, '_bset:%s: configs: %s'  % (self.bset, ','.join(configs)))

        current_path = os.environ['PATH']
        try:
            builds = []
            for s in range(0, len(configs)):
                if configs[s].endswith('.bset'):
                    bs = buildset(configs[s], _configs = self.configs, _defaults = self.defaults, opts = self.opts)
                    bs.build()
                    del bs
                elif configs[s].endswith('.cfg'):
                    b = build.build(configs[s], _defaults = self.defaults, opts = self.opts)
                    if s == 0:
                        tmproot = self.first_package(b)
                    b.make()
                    self.every_package(b, tmproot)
                    if s == len(configs) - 1:
                        self.last_package(b, tmproot)
                    builds += [b]
                else:
                    raise error.general('invalid config type: %s' % (configs[s]))
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
        optargs = { '--list-configs': 'List available configurations',
                    '--list-bsets': 'List available build sets'}
        opts, _defaults = defaults.load(sys.argv, optargs)
        log.default = log.log(opts.logfiles())
        _notice(opts, 'Source Builder - Set Builder, v%s' % (version))
        if not check.host_setup(opts, _defaults):
            raise error.general('host build environment is not set up correctly')
        configs = build.get_configs(opts, _defaults)
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
        else:
            for bset in opts.params():
                b = buildset(bset, _configs = configs, _defaults = _defaults, opts = opts)
                b.build()
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
    run()
