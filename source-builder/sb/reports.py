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

import copy
import datetime
import os
import sys

import pprint
pp = pprint.PrettyPrinter(indent = 2)

try:
    import build
    import check
    import config
    import error
    import git
    import log
    import options
    import path
    import setbuilder
    import sources
    import version
except KeyboardInterrupt:
    print 'user terminated'
    sys.exit(1)
except:
    print 'error: unknown application load error'
    sys.exit(1)

def _tree_name(path_):
    return path.splitext(path.basename(path_))[0]

def _merge(_dict, new):
    new = copy.deepcopy(new)
    for i in new:
        if i not in _dict:
            _dict[i] = new[i]
        else:
            _dict[i] += new[i]

class report:
    """Report the build details about a package given a config file."""

    line_len = 78

    def __init__(self, format, _configs, opts, macros = None):
        self.format = format
        self.configs = _configs
        self.opts = opts
        if macros is None:
            self.macros = opts.defaults
        else:
            self.macros = macros
        self.bset_nesting = 0
        self.configs_active = False
        self.out = ''
        self.asciidoc = None
        if self.is_ini():
            self.cini = ';'
        else:
            self.cini = ''
        self.tree = {}
        self.files = { 'buildsets':[], 'configs':[] }

    def _sbpath(self, *args):
        p = self.macros.expand('%{_sbdir}')
        for arg in args:
            p = path.join(p, arg)
        return os.path.abspath(path.host(p))

    def output(self, text):
        self.out += '%s\n' % (text)

    def is_text(self):
        return self.format == 'text'

    def is_asciidoc(self):
        return self.format == 'asciidoc' or self.format == 'html'

    def is_html(self):
        return self.format == 'html'

    def is_ini(self):
        return self.format == 'ini'

    def setup(self):
        if self.is_html():
            try:
                import asciidocapi
            except:
                raise error.general('installation error: no asciidocapi found')
            asciidoc_py = self._sbpath(options.basepath, 'asciidoc', 'asciidoc.py')
            try:
                self.asciidoc = asciidocapi.AsciiDocAPI(asciidoc_py)
            except:
                raise error.general('application error: asciidocapi failed')

    def header(self):
        pass

    def footer(self):
        pass

    def git_status(self):
        text = 'RTEMS Source Builder Repository Status'
        if self.is_asciidoc():
            self.output('')
            self.output("'''")
            self.output('')
            self.output('.%s' % (text))
        elif self.is_ini():
            self.output(';')
            self.output('; %s' % (text))
            self.output(';')
        else:
            self.output('-' * self.line_len)
            self.output('%s' % (text))
        repo = git.repo('.', self.opts, self.macros)
        repo_valid = repo.valid()
        if repo_valid:
            if self.is_asciidoc():
                self.output('*Remotes*:;;')
            else:
                self.output('%s Remotes:' % (self.cini))
            repo_remotes = repo.remotes()
            rc = 0
            for r in repo_remotes:
                rc += 1
                if 'url' in repo_remotes[r]:
                    text = repo_remotes[r]['url']
                else:
                    text = 'no URL found'
                text = '%s: %s' % (r, text)
                if self.is_asciidoc():
                    self.output('. %s' % (text))
                else:
                    self.output('%s  %2d: %s' % (self.cini, rc, text))
            if self.is_asciidoc():
                self.output('*Status*:;;')
            else:
                self.output('%s Status:' % (self.cini))
            if repo.dirty():
                if self.is_asciidoc():
                    self.output('_Repository is dirty_')
                else:
                    self.output('%s  Repository is dirty' % (self.cini))
            else:
                if self.is_asciidoc():
                    self.output('Clean')
                else:
                    self.output('%s  Clean' % (self.cini))
            repo_head = repo.head()
            if self.is_asciidoc():
                self.output('*Head*:;;')
                self.output('Commit: %s' % (repo_head))
            else:
                self.output('%s Head:' % (self.cini))
                self.output('%s  Commit: %s' % (self.cini, repo_head))
        else:
            if self.is_asciidoc():
                self.output('_Not a valid GIT repository_')
            else:
                self.output('%s Not a valid GIT repository' % (self.cini))
        if self.is_asciidoc():
            self.output('')
            self.output("'''")
            self.output('')

    def introduction(self, name, intro_text = None):
        now = datetime.datetime.now().ctime()
        title = 'RTEMS Tools Project <users@rtems.org>'
        if self.is_asciidoc():
            h = 'RTEMS Source Builder Report'
            self.output(h)
            self.output('=' * len(h))
            self.output(':doctype: book')
            self.output(':toc2:')
            self.output(':toclevels: 5')
            self.output(':icons:')
            self.output(':numbered:')
            self.output(':data-uri:')
            self.output('')
            self.output(title)
            self.output(datetime.datetime.now().ctime())
            self.output('')
            image = self._sbpath(options.basepath, 'images', 'rtemswhitebg.jpg')
            self.output('image:%s["RTEMS",width="20%%"]' % (image))
            self.output('')
            if intro_text:
                self.output('%s' % ('\n'.join(intro_text)))
        elif self.is_ini():
            self.output(';')
            self.output('; %s %s' % (title, now))
            if intro_text:
                self.output(';')
                self.output('; %s' % ('\n; '.join(intro_text)))
                self.output(';')
        else:
            self.output('=' * self.line_len)
            self.output('%s %s' % (title, now))
            if intro_text:
                self.output('')
                self.output('%s' % ('\n'.join(intro_text)))
            self.output('=' * self.line_len)
            self.output('Report: %s' % (name))
        self.git_status()

    def config_start(self, name, _config):
        self.files['configs'] += [name]
        for cf in _config.includes():
            cfbn = path.basename(cf)
            if cfbn not in self.files['configs']:
                self.files['configs'] += [cfbn]
        first = not self.configs_active
        self.configs_active = True

    def config_end(self, name, _config):
        if self.is_asciidoc():
            self.output('')
            self.output("'''")
            self.output('')

    def buildset_start(self, name):
        self.files['buildsets'] += [name]
        if self.is_asciidoc():
            h = '%s' % (name)
            self.output('=%s %s' % ('=' * self.bset_nesting, h))
        elif self.is_ini():
            pass
        else:
            self.output('=-' * (self.line_len / 2))
            self.output('Build Set: %s' % (name))

    def buildset_end(self, name):
        self.configs_active = False

    def source(self, macros):
        def err(msg):
            raise error.general('%s' % (msg))
        _srcs = {}
        for p in sources.get_source_names(macros, err):
            if 'setup' in sources.get_source_keys(p, macros, err):
                _srcs[p] = \
                    [s for s in sources.get_sources(p, macros, err) if not s.startswith('%setup')]
                _srcs[p] = [macros.expand(s) for s in _srcs[p]]
        srcs = {}
        for p in _srcs:
            srcs[p] = [(s, sources.get_hash(path.basename(s).lower(), macros)) for s in _srcs[p]]
        return srcs

    def patch(self, macros):
        def err(msg):
            raise error.general('%s' % (msg))
        _patches = {}
        for n in sources.get_patch_names(macros, err):
            if 'setup' in sources.get_patch_keys(n, macros, err):
                _patches[n] = \
                    [p for p in sources.get_patches(n, macros, err) if not p.startswith('%setup')]
                _patches[n] = [macros.expand(p.split()[-1]) for p in _patches[n]]
        patches = {}
        for n in _patches:
            patches[n] = [(p, sources.get_hash(path.basename(p).lower(), macros)) for p in _patches[n]]
        return patches

    def output_info(self, name, info, separated = False):
        if info is not None:
            end = ''
            if self.is_asciidoc():
                if separated:
                    self.output('*%s:*::' % (name))
                    self.output('')
                else:
                    self.output('*%s:* ' % (name))
                    end = ' +'
                spaces = ''
            else:
                self.output(' %s:' % (name))
                spaces = '  '
            for l in info:
                self.output('%s%s%s' % (spaces, l, end))
            if self.is_asciidoc() and separated:
                self.output('')

    def output_directive(self, name, directive):
        if directive is not None:
            if self.is_asciidoc():
                self.output('')
                self.output('*%s*:' % (name))
                self.output('--------------------------------------------')
                spaces = ''
            else:
                self.output(' %s:' % (name))
                spaces = '  '
            for l in directive:
                self.output('%s%s' % (spaces, l))
            if self.is_asciidoc():
                self.output('--------------------------------------------')

    def tree_sources(self, name, tree, sources = []):
        if 'cfg' in tree:
            packages = {}
            if 'sources' in tree['cfg']:
                _merge(packages, tree['cfg']['sources'])
            if 'patches' in tree['cfg']:
                _merge(packages, tree['cfg']['patches'])
            for package in packages:
                for source in packages[package]:
                    if not source[0].startswith('git') and not source[0].startswith('cvs'):
                        sources += [(path.basename(source[0]), source[0], source[1])]
        if 'bset' in tree:
            for node in sorted(tree['bset'].keys()):
                self.tree_sources(_tree_name(node), tree['bset'][node], sources)
        return sources

    def config(self, _config, tree, opts, macros):
        packages = _config.packages()
        package = packages['main']
        name = package.name()
        if len(name) == 0:
            return
        tree['file'] += [_config.file_name()]
        sources = self.source(macros)
        patches = self.patch(macros)
        if len(sources):
            if 'sources' in tree:
                tree['sources'] = dict(tree['sources'].items() + sources.items())
            else:
                tree['sources'] = sources
        if len(patches):
            if 'patches' in tree:
                tree['patches'] = dict(tree['patches'].items() + patches.items())
            else:
                tree['patches'] = patches
        self.config_start(name, _config)
        if self.is_ini():
            return
        if self.is_asciidoc():
            self.output('*Package*: _%s_ +' % (name))
            self.output('*Config*: %s' % (_config.file_name()))
            self.output('')
        else:
            self.output('-' * self.line_len)
            self.output('Package: %s' % (name))
            self.output(' Config: %s' % (_config.file_name()))
        self.output_info('Summary', package.get_info('summary'), True)
        self.output_info('URL', package.get_info('url'))
        self.output_info('Version', package.get_info('version'))
        self.output_info('Release', package.get_info('release'))
        self.output_info('Build Arch', package.get_info('buildarch'))
        if self.is_asciidoc():
            self.output('')
        if self.is_asciidoc():
            self.output('*Sources:*::')
            if len(sources) == 0:
                self.output('No sources')
        else:
            self.output('  Sources: %d' % (len(sources)))
        c = 0
        for name in sources:
            for s in sources[name]:
                c += 1
                if self.is_asciidoc():
                    self.output('. %s' % (s[0]))
                else:
                    self.output('   %2d: %s' % (c, s[0]))
                if s[1] is None:
                    h = 'No checksum'
                else:
                    hash = s[1].split()
                    h = '%s: %s' % (hash[0], hash[1])
                if self.is_asciidoc():
                    self.output('+\n%s\n' % (h))
                else:
                    self.output('       %s' % (h))
        if self.is_asciidoc():
            self.output('')
            self.output('*Patches:*::')
            if len(patches) == 0:
                self.output('No patches')
        else:
            self.output('  Patches: %s' % (len(patches)))
        c = 0
        for name in patches:
            for p in patches[name]:
                c += 1
                if self.is_asciidoc():
                    self.output('. %s' % (p[0]))
                else:
                    self.output('   %2d: %s' % (c, p[0]))
                hash = p[1]
                if hash is None:
                    h = 'No checksum'
                else:
                    hash = hash.split()
                    h = '%s: %s' % (hash[0], hash[1])
                if self.is_asciidoc():
                    self.output('+\n(%s)\n' % (h))
                else:
                    self.output('       %s' % (h))
        self.output_directive('Preparation', package.prep())
        self.output_directive('Build', package.build())
        self.output_directive('Install', package.install())
        self.output_directive('Clean', package.clean())
        self.config_end(name, _config)

    def generate_ini_tree(self, name, tree, prefix_char, prefix = ''):
        if prefix_char == '|':
            c = '|'
        else:
            c = '+'
        self.output('; %s  %s- %s' % (prefix, c, name))
        prefix += '  %s ' % (prefix_char)
        if 'cfg' in tree:
            files = sorted(tree['cfg']['file'])
            if len(files):
                for f in range(0, len(files) - 1):
                    self.output('; %s  |- %s' % (prefix, files[f]))
                if 'bset' in tree and len(tree['bset'].keys()):
                    c = '|'
                else:
                    c = '+'
                self.output('; %s  %s- %s' % (prefix, c, files[f + 1]))
        if 'bset' in tree:
            nodes = sorted(tree['bset'].keys())
            for node in range(0, len(nodes)):
                if node == len(nodes) - 1:
                    prefix_char = ' '
                else:
                    prefix_char = '|'
                self.generate_ini_tree(nodes[node],
                                       tree['bset'][nodes[node]],
                                       prefix_char,
                                       prefix)

    def generate_ini_node(self, name, tree, sections = []):
        if name not in sections:
            sections += [name]
            self.output('')
            self.output('[%s]' % (name))
            if 'bset' in tree and len(tree['bset']):
                self.output(' packages = %s' % \
                                (', '.join([_tree_name(n) for n in sorted(tree['bset'])])))
            if 'cfg' in tree:
                packages = {}
                if 'sources' in tree['cfg']:
                    _merge(packages, tree['cfg']['sources'])
                if 'patches' in tree['cfg']:
                    _merge(packages, tree['cfg']['patches'])
                for package in packages:
                    self.output(' %s = %s' % (package, ', '.join([s[0] for s in packages[package]])))
            if 'bset' in tree:
                for node in sorted(tree['bset'].keys()):
                    self.generate_ini_node(_tree_name(node), tree['bset'][node], sections)

    def generate_ini_source(self, sources):
        self.output('')
        self.output('[source]')
        for source in sources:
            self.output(' %s = %s' % (source[0], source[1]))

    def generate_ini_hash(self, sources):
        self.output('')
        self.output('[hash]')
        for source in sources:
            if source[2] is None:
                hash = ''
            else:
                hash = source[2].split()
                hash = '%s:%s' % (hash[0], hash[1])
            self.output(' %s = %s' % (source[0], hash))

    def generate_ini(self):
        #self.output(pp.pformat(self.tree))
        nodes = sorted([node for node in self.tree.keys() if node != 'bset'])
        self.output(';')
        self.output('; Configuration Tree:')
        for node in range(0, len(nodes)):
            if node == len(nodes) - 1:
                prefix_char = ' '
            else:
                prefix_char = '|'
            self.generate_ini_tree(nodes[node], self.tree[nodes[node]], prefix_char)
        self.output(';')
        sources = []
        for node in nodes:
            sources += self.tree_sources(_tree_name(node), self.tree[node])
        sources = sorted(set(sources))
        self.generate_ini_source(sources)
        self.generate_ini_hash(sources)
        for node in nodes:
            self.generate_ini_node(_tree_name(node), self.tree[node])

    def write(self, name):
        if self.is_html():
            if self.asciidoc is None:
                raise error.general('asciidoc not initialised')
            import StringIO
            infile = StringIO.StringIO(self.out)
            outfile = StringIO.StringIO()
            self.asciidoc.execute(infile, outfile)
            self.out = outfile.getvalue()
            infile.close()
            outfile.close()
        elif self.is_ini():
            self.generate_ini()
        if name is not None:
            try:
                o = open(path.host(name), "w")
                o.write(self.out)
                o.close()
                del o
            except IOError, err:
                raise error.general('writing output file: %s: %s' % (name, err))

    def generate(self, name, tree = None, opts = None, defaults = None):
        self.bset_nesting += 1
        self.buildset_start(name)
        if tree is None:
            tree = self.tree
        if opts is None:
            opts = self.opts
        bset = setbuilder.buildset(name, self.configs, opts, defaults)
        if name in tree:
            raise error.general('duplicate build set in tree: %s' % (name))
        tree[name] = { 'bset': { }, 'cfg': { 'file': []  } }
        for c in bset.load():
            macros = copy.copy(bset.macros)
            if c.endswith('.bset'):
                self.generate(c, tree[name]['bset'], bset.opts, macros)
            elif c.endswith('.cfg'):
                self.config(config.file(c, bset.opts, macros),
                            tree[name]['cfg'], bset.opts, macros)
            else:
                raise error.general('invalid config type: %s' % (c))
        self.buildset_end(name)
        self.bset_nesting -= 1

    def create(self, inname, outname = None, intro_text = None):
        self.setup()
        self.introduction(inname, intro_text)
        self.generate(inname)
        self.write(outname)

def run(args):
    try:
        optargs = { '--list-bsets':   'List available build sets',
                    '--list-configs': 'List available configurations',
                    '--format':       'Output format (text, html, asciidoc, ini)',
                    '--output':       'File name to output the report' }
        opts = options.load(args, optargs)
        if opts.get_arg('--output') and len(opts.params()) > 1:
            raise error.general('--output can only be used with a single config')
        print 'RTEMS Source Builder, Reporter v%s' % (version.str())
        opts.log_info()
        if not check.host_setup(opts):
            log.warning('forcing build with known host setup problems')
        configs = build.get_configs(opts)
        if not setbuilder.list_bset_cfg_files(opts, configs):
            output = opts.get_arg('--output')
            if output is not None:
                output = output[1]
            format = 'text'
            ext = '.txt'
            format_opt = opts.get_arg('--format')
            if format_opt:
                if len(format_opt) != 2:
                    raise error.general('invalid format option: %s' % ('='.join(format_opt)))
                if format_opt[1] == 'text':
                    pass
                elif format_opt[1] == 'asciidoc':
                    format = 'asciidoc'
                    ext = '.txt'
                elif format_opt[1] == 'html':
                    format = 'html'
                    ext = '.html'
                elif format_opt[1] == 'ini':
                    format = 'ini'
                    ext = '.ini'
                else:
                    raise error.general('invalid format: %s' % (format_opt[1]))
            r = report(format, configs, opts)
            for _config in opts.params():
                if output is None:
                    outname = path.splitext(_config)[0] + ext
                    outname = outname.replace('/', '-')
                else:
                    outname = output
                config = build.find_config(_config, configs)
                if config is None:
                    raise error.general('config file not found: %s' % (inname))
                r.create(config, outname)
            del r
        else:
            raise error.general('invalid config type: %s' % (config))
    except error.general, gerr:
        print gerr
        sys.exit(1)
    except error.internal, ierr:
        print ierr
        sys.exit(1)
    except error.exit, eerr:
        pass
    except KeyboardInterrupt:
        log.notice('abort: user terminated')
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    run(sys.argv)
