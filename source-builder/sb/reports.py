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
# This code builds a package given a config file. It only builds to be
# installed not to be package unless you run a packager around this.
#

import os
import sys

import build
import check
import config
import defaults
import error
import log
import setbuilder

#
# Version of Sourcer Builder Build.
#
version = '0.1'

def _notice(opts, text):
    if not opts.quiet() and not log.default.has_stdout():
        print text
    log.output(text)
    log.flush()

class report:
    """Report the build details about a package given a config file."""

    line_len = 78

    def __init__(self, name, format, _configs, _defaults, opts):
        self.format = format
        self.name = name
        self.configs = _configs
        self.defaults = _defaults
        self.opts = opts
        self.bset_nesting = 0
        self.configs_active = False

    def _output(self, text):
        if not self.opts.quiet():
            log.output(text)

    def is_text(self):
        return self.format == 'text'

    def is_asciidoc(self):
        return self.format == 'asciidoc'

    def setup(self):
        if self.is_asciidoc():
            pass

    def header(self):
        pass

    def footer(self):
        pass

    def introduction(self, name):
        if self.is_asciidoc():
            h = 'RTEMS Source Builder Report'
            log.output(h)
            log.output('=' * len(h))
            log.output(':doctype: book')
            log.output(':toc2:')
            log.output(':toclevels: 5')
            log.output(':icons:')
            log.output(':numbered:')
            log.output(' ')
            log.output('RTEMS Project <rtems-user@rtems.org>')
            log.output('28th Feb 2013')
            log.output(' ')
        else:
            log.output('report: %s' % (name))

    def config_start(self, name):
        first = not self.configs_active
        self.configs_active = True
        if self.is_asciidoc():
            log.output('.Config: %s' % name)
            log.output('')
        else:
            log.output('-' * self.line_len)
            log.output('config: %s' % (name))

    def config_end(self, name):
        if self.is_asciidoc():
            log.output(' ')
            log.output("'''")
            log.output(' ')

    def buildset_start(self, name):
        if self.is_asciidoc():
            h = '%s' % (name)
            log.output('=%s %s' % ('=' * self.bset_nesting, h))
        else:
            log.output('=' * self.line_len)
            log.output('build set: %s' % (name))

    def buildset_end(self, name):
        self.configs_active = False

    def source(self, package, source_tag):
        return package.sources()

    def patch(self, package, args):
        return package.patches()

    def config(self, name):
        self.config_start(name)
        _config = config.file(name, _defaults = self.defaults, opts = self.opts)
        packages = _config.packages()
        package = packages['main']
        name = package.name()
        if self.is_asciidoc():
            log.output('*Package*: _%s_' % name)
            log.output(' ')
        else:
            log.output(' package: %s' % (name))
        sources = package.sources()
        if self.is_asciidoc():
            log.output('*Sources*;;')
            if len(sources) == 0:
                log.output('No sources')
        else:
            log.output('  sources: %d' % (len(sources)))
        c = 0
        for s in sources:
            c += 1
            if self.is_asciidoc():
                log.output('. %s' % (sources[s][0]))
            else:
                log.output('   %2d: %s' % (c, sources[s][0]))
        patches = package.patches()
        if self.is_asciidoc():
            log.output(' ')
            log.output('*Patches*:;;')
            if len(patches) == 0:
                log.output('No patches')
        else:
            log.output('  patches: %s' % (len(patches)))
        c = 0
        for p in patches:
            c += 1
            if self.is_asciidoc():
                log.output('. %s' % (patches[p][0]))
            else:
                log.output('   %2d: %s' % (c, patches[p][0]))
        self.config_end(name)

    def buildset(self, name):
        try_config = False
        try:
            self.bset_nesting += 1
            self.buildset_start(name)
            bset = setbuilder.buildset(name,
                                       _configs = self.configs,
                                       _defaults = self.defaults,
                                       opts = self.opts)
            for c in bset.load():
                if c.endswith('.bset'):
                    self.buildset(c)
                elif c.endswith('.cfg'):
                    self.config(c)
                else:
                    raise error.general('invalid config type: %s' % (c))
            self.buildset_end(name)
            self.bset_nesting -= 1
        except error.general, gerr:
            if gerr.msg.startswith('no build set file found'):
                try_config = True
            else:
                raise
        if try_config:
            self.config(name)

    def generate(self):
        self.introduction(self.name)
        self.buildset(self.name)

def run(args):
    try:
        optargs = { '--list-bsets':   'List available build sets',
                    '--list-configs': 'List available configurations',
                    '--asciidoc':     'Output report as asciidoc' }
        opts, _defaults = defaults.load(args, optargs)
        log.default = log.log(opts.logfiles())
        print 'RTEMS Source Builder, Reporter v%s' % (version)
        if not check.host_setup(opts, _defaults):
            _notice(opts, 'warning: forcing build with known host setup problems')
        configs = build.get_configs(opts, _defaults)
        if not setbuilder.list_bset_cfg_files(opts, configs):
            format = 'text'
            if opts.get_arg('--asciidoc'):
                format = 'asciidoc'
            for _file in opts.params():
                r = report(_file,
                           format = format,
                           _configs = configs,
                           _defaults = _defaults,
                           opts = opts)
                r.generate()
                del r
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
    run(sys.argv)
