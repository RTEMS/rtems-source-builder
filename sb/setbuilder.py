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
import operator
import os

import build
import defaults
import error
import log

#
# Version of Tools Builder CrossGCC Builder.
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

class crossgcc:
    """Build a Cross GCC Compiler tool suite."""

    _order = { 'binutils': 0,
               'gcc'     : 1,
               'gdb'     : 2 }

    def __init__(self, toolset, _defaults, opts):
        _trace(opts, '_cgcc:%s: init' % (toolset))
        self.opts = opts
        self.defaults = _defaults
        self.toolset = toolset
        self.toolset_pkg = '%s-%s-tools' % (self.opts.expand('%{_target}', _defaults),
                                            self.toolset)

    def _output(self, text):
        if not self.opts.quiet():
            log.output(text)

    def copy(self, src, dst):
        if os.path.isdir(src):
            topdir = self.opts.expand('%{_topdir}', self.defaults)
            what = '%s -> %s' % (src[len(topdir) + 1:], dst[len(topdir) + 1:])
            _notice(self.opts, 'installing: %s' % (what))
            if not self.opts.dry_run():
                try:
                    files = distutils.dir_util.copy_tree(src, dst)
                    for f in files:
                        self._output(f)
                except IOError, err:
                    raise error.general('installing tree: %s: %s' % (what, str(err)))
                except distutils.errors.DistutilsFileError, err:
                    raise error.general('installing tree: %s' % (str(err)))

    def first_package(self, _build):
        tmproot = os.path.abspath(_build.config.expand('%{_tmproot}'))
        _build.rmdir(tmproot)
        _build.mkdir(tmproot)
        prefix = _build.config.expand('%{_prefix}')
        if prefix[0] == os.sep:
            prefix = prefix[1:]
        tmpprefix = os.path.join(tmproot, prefix)
        tmpbindir = os.path.join(tmpprefix, 'bin')
        os.environ['SB_TMPPREFIX'] = tmpprefix
        os.environ['SB_TMPBINDIR'] = tmpbindir
        os.environ['PATH'] = tmpbindir + os.pathsep + os.environ['PATH']
        self._output('path: ' + os.environ['PATH'])
        return tmproot

    def every_package(self, _build, path):
        self.copy(_build.config.abspath('%{buildroot}'), path)

    def last_package(self, _build, path):
        tar = os.path.join(_build.config.expand('%{_tardir}'),
                           _build.config.expand('%s.tar.bz2' % (self.toolset_pkg)))
        _notice(self.opts, 'tarball: %s' % (tar))
        if not self.opts.dry_run():
            cmd = _build.config.expand("'cd " + path + \
                                           " && %{__tar} -cf - . | %{__bzip2} > " + tar + "'")
            _build.run(cmd, shell_opts = '-c', cwd = path)

        #if not self.opts.no_clean():
        #    _build.rmdir(path)

    def load(self):

        def _clean(line):
            line = line[0:-1]
            b = line.find('#')
            if b >= 0:
                line = line[1:b]
            return line.strip()

        extoolset = self.opts.expand(self.toolset, self.defaults)

        self.defaults['_toolset'] = extoolset

        root, ext = os.path.splitext(extoolset)

        if extoolset.endswith('.cfg'):
            toolsetcfg = extoolset
        else:
            toolsetcfg = '%s.cfg' % (extoolset)

        toolsetname = toolsetcfg

        if not os.path.exists(toolsetname):
            for cp in self.opts.expand('%{_configdir}', self.defaults).split(':'):
                configdir = os.path.abspath(cp)
                toolsetname = os.path.join(configdir, toolsetcfg)
                if os.path.exists(toolsetname):
                    break
                toolsetname = None
            if toolsetname is None:
                raise error.general('no tool set file found: %s' % (toolsetcfg))
        try:
            if self.opts.trace():
                print '_cgcc:%s: open: %s' % (self.toolset, toolsetname)
            toolset = open(toolsetname, 'r')
        except IOError, err:
            raise error.general('error opening toolset file: %s' + toolsetname)

        configs = []

        try:
            lc = 0
            for l in toolset:
                lc += 1
                l = _clean(l)
                if len(l) == 0:
                    continue
                if self.opts.trace():
                    print '%03d: %s' % (lc, l)
                if ':' in l:
                    ls = l.split(':')
                    if ls[0].strip() == 'package':
                        self.toolset_pkg = self.opts.expand(ls[1].strip(), self.defaults)
                        self.defaults['package'] = self.toolset_pkg
                elif l[0] == '%':
                    if l.startswith('%define'):
                        ls = l.split()
                        self.defaults[ls[1].strip()] = ls[2].strip()
                    else:
                        raise error.general('invalid directive in tool set files: %s' % (l))
                else:
                    configs += [l.strip()]
        except:
            toolset.close()
            raise

        toolset.close()

        return configs

    def make(self):

        def _sort(configs):
            _configs = {}
            for config in configs:
                for order in crossgcc._order:
                    if config.lower().find(order) >= 0:
                        _configs[config] = crossgcc._order[order]
            sorted_configs = sorted(_configs.iteritems(), key = operator.itemgetter(1))
            configs = []
            for s in range(0, len(sorted_configs)):
                configs.append(sorted_configs[s][0])
            return configs

        _trace(self.opts, '_cgcc:%s: make' % (self.toolset))
        _notice(self.opts, 'toolset: %s' % (self.toolset))

        configs = self.load()

        _trace(self.opts, '_cgcc:%s: configs: %s'  % (self.toolset, ','.join(configs)))

        current_path = os.environ['PATH']
        try:
            builds = []
            for s in range(0, len(configs)):
                b = build.build(configs[s], _defaults = self.defaults, opts = self.opts)
                if s == 0:
                    path = self.first_package(b)
                b.make(path)
                self.every_package(b, path)
                if s == len(configs) - 1:
                    self.last_package(b, path)
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
        opts, _defaults = defaults.load(sys.argv)
        log.default = log.log(opts.logfiles())
        _notice(opts, 'Tools Builder - CrossGCC Tool Sets, v%s' % (version))
        for toolset in opts.params():
            c = crossgcc(toolset, _defaults = _defaults, opts = opts)
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
