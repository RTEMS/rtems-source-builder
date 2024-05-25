#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2015 Chris Johns (chrisj@rtems.org)
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

from __future__ import print_function

import base64
import copy
import datetime
import os
import sys

try:
    from . import build
    from . import check
    from . import config
    from . import error
    from . import git
    from . import log
    from . import options
    from . import path
    from . import sources
    from . import version
except KeyboardInterrupt:
    print('user terminated', file=sys.stderr)
    sys.exit(1)
except:
    raise

_line_len = 78

_title = 'RTEMS Tools Project <users@rtems.org>'

_release_status_text = 'RTEMS Source Builder Release'
_git_status_text = 'RTEMS Source Builder Repository Status'


def _make_path(p, *args):
    for arg in args:
        p = path.join(p, arg)
    return os.path.abspath(path.host(p))


def platform(mode='all'):
    import platform
    if mode == 'system':
        return platform.system()
    compact = platform.platform(aliased=True)
    if mode == 'compact':
        return compact
    extended = ' '.join(platform.uname())
    if mode == 'extended':
        return extended
    return '%s (%s)' % (short, extended)


class formatter(object):

    def __init__(self):
        self.content = ''

    def line(self, text):
        self.content += text + '\n'

    def add(self, text):
        self.content += text

    def set_sbpath(self, sbpath):
        self.sbpath = sbpath

    def format(self):
        raise error.general(
            'internal error: formatter.format() not implemented')

    def ext(self):
        raise error.general('internal error: formatter.ext() not implemented')

    def introduction(self, name, now, intro_text):
        self.line('=' * _line_len)
        self.line('%s %s' % (_title, now))
        if intro_text:
            self.line('')
            self.line('%s' % ('\n'.join(intro_text)))
        self.line('=' * _line_len)
        self.line('Report: %s' % (name))

    def epilogue(self, name):
        return

    def config_start(self, nest_level, name):
        return

    def config(self, nest_level, name, _config):
        self.line('-' * _line_len)
        self.line('Package: %s' % (name))
        self.line(' Config: %s' % (_config.file_name()))

    def config_end(self, nest_level, name):
        return

    def buildset_start(self, nest_level, name):
        self.line('=-' * int(_line_len / 2))
        self.line('Build Set: (%d) %s' % (nest_level, name))

    def buildset_end(self, nest_level, name):
        return

    def info(self, nest_level, name, info, separated):
        self.line(' ' + name + ':')
        for l in info:
            self.line('  ' + l)

    def directive(self, nest_level, name, data):
        self.line(' %s:' % (name))
        for l in data:
            self.line('  ' + l)

    def files(self, nest_level, sigular, plural, _files):
        self.line('  ' + plural + ': %d' % (len(_files)))
        i = 0
        for name in _files:
            for s in _files[name]:
                i += 1
                self.line('   %2d: %s' % (i, s[0]))
                if s[1] is None:
                    h = 'No checksum'
                else:
                    hash = s[1].split()
                    h = '%s: %s' % (hash[0], hash[1])
                self.line('       %s' % (h))

    def post_process(self):
        return self.content


class markdown_formatter(formatter):

    def __init__(self):
        super(markdown_formatter, self).__init__()
        self.level_current = 1
        self.level_path = '0.'
        self.levels = {'0.': 0}
        self.cols = [20, 55]

    def _heading(self, heading, level):
        return '%s %s' % ('#' * level, heading)

    def _strong(self, s):
        return '__' + s + '__'

    def _bold(self, s):
        return '__' + s + '__'

    def _italic(self, s):
        return '_' + s + '_'

    def _table_line(self):
        l = '|'
        for c in self.cols:
            l += '-' * c + '|'
        return l

    def _table_row(self, cols):
        if len(cols) != len(self.cols):
            raise error.general('invalid table column count')
        l = '|'
        for c in range(0, len(cols)):
            l += '%-*s|' % (self.cols[c], cols[c])
        return l

    def _btext(self, level, text):
        return '> ' * (level - 1) + text

    def _bline(self, level, text):
        self.line(self._btext(level, text))

    def _level(self, nest_level):
        if nest_level > self.level_current:
            self.level_path += '%d.' % (self.levels[self.level_path])
        if nest_level < self.level_current:
            self.level_path = self.level_path[:-2]
        if self.level_path not in self.levels:
            self.levels[self.level_path] = 0
        self.level_current = nest_level
        self.levels[self.level_path] += 1
        return '%s%d.' % (self.level_path[2:], self.levels[self.level_path])

    def format(self):
        return 'markdown'

    def ext(self):
        return '.md'

    def introduction(self, name, now, intro_text):
        self.line('- - -')
        self.line(self._heading('RTEMS Source Builder Report', 1))
        self.line(self._strong(_title))
        self.line('')
        self.line(self._bold('Generated: ' + now))
        self.line('')
        if intro_text:
            self.line('%s' % ('\n'.join(intro_text)))
            self.line('')
        self.line('')
        self.line('- - -')
        self.line(self._heading('Table Of Contents', 2))
        self.line('')
        self.line('[TOC]')
        self.line('')

    def release_status(self, release_string):
        self.line('')
        self.line(self._heading(_release_status_text, 2))
        self.line('')
        self.line('*Version*: %s;;' % (release_string))
        self.line('')

    def git_status(self, valid, dirty, head, remotes):
        self.line('')
        self.line('- - -')
        self.line(self._heading(_git_status_text, 2))
        if valid:
            self.line(self._strong('Remotes:'))
            self.line('')
            rc = 1
            if not remotes:
                self.line('[ remotes removed, contact sender for details ]')
            else:
                for r in remotes:
                    if 'url' in remotes[r]:
                        text = remotes[r]['url']
                    else:
                        text = 'no URL found'
                    self.line('%d. %s: %s' % (rc, r, text))
                    rc += 1
            self.line('')
            self.line(self._strong('Status:'))
            self.line('')
            if dirty:
                self.line('> ' + self._italic('Repository is dirty'))
            else:
                self.line('> Clean')
            self.line('>')
            self.line('> ' + self._bold('Head: ') + head)
        else:
            self.line('> ' + self._italic('Not a valid GIT repository'))
        self.line('')

    def config(self, nest_level, name, _config):
        self._bline(nest_level, self._bold('Package:'))
        self._bline(nest_level, '')
        self._bline(
            nest_level + 1,
            self._table_row([self._bold('Item'),
                             self._bold('Description')]))
        self._bline(nest_level + 1, self._table_line())
        self._bline(nest_level + 1, self._table_row(['Package', name]))
        self._bline(nest_level + 1,
                    self._table_row(['Config', _config.file_name()]))

    def config_end(self, nest_level, name):
        self._bline(nest_level + 1, '')

    def buildset_start(self, nest_level, name):
        if nest_level == 1:
            self.line('- - -')
            self._bline(nest_level,
                        self._heading('RTEMS Source Builder Packages', 2))
        self._bline(
            nest_level,
            self._heading('%s Build %s' % (self._level(nest_level), name), 3))

    def info(self, nest_level, name, info, separated):
        self._bline(nest_level + 1, self._table_row([name, ' '.join(info)]))

    def directive(self, nest_level, name, data):
        self._bline(nest_level, '')
        self._bline(nest_level, self._bold(name + ':'))
        for l in data:
            self._bline(nest_level + 1, ' ' * 4 + l)

    def files(self, nest_level, singular, plural, _files):
        self._bline(nest_level, '')
        self._bline(nest_level, self._bold(plural + ':'))
        self._bline(nest_level, '')
        if len(_files) == 0:
            self._bline(nest_level + 1, 'No ' + plural.lower())
        fc = 0
        for name in _files:
            for s in _files[name]:
                fc += 1
                if s[1] is None:
                    h = self._bold('No checksum')
                else:
                    hash = s[1].split()
                    h = '%s: %s' % (hash[0], hash[1])
                self._bline(
                    nest_level, '%d. [%s](%s "%s %s")<br/>' %
                    (fc, s[0], s[0], name, singular.lower()))
                self._bline(nest_level,
                            '    <span class=checksum>%s</span>' % (h))


class html_formatter(markdown_formatter):

    def __init__(self):
        super(html_formatter, self).__init__()
        self.html_header = '<!DOCTYPE html>' + os.linesep + \
                           '<html lang="en">' + os.linesep + \
                           '<head>' + os.linesep + \
                           '<title>RTEMS RSB - @BUILD@</title>' + os.linesep + \
                           '<meta http-equiv="content-type" content="text/html; charset=UTF-8" />' + os.linesep + \
                           '<meta name="created" content="@NOW@" />' + os.linesep + \
                           '<meta name="description" content="RTEMS RSB Report" />' + os.linesep + \
                           '<meta name="keywords" content="RTEMS RSB" />' + os.linesep + \
                           '<meta charset="utf-8">' + os.linesep + \
                           '<meta http-equiv="X-UA-Compatible" content="IE=edge">' + os.linesep + \
                           '<meta name="viewport" content="width=device-width, initial-scale=1">' + os.linesep + \
                           '<style type="text/css">' + os.linesep + \
                           'body {' + os.linesep + \
                           ' font-family: arial, helvetica, serif;' + os.linesep + \
                           ' font-style: normal;' + os.linesep + \
                           ' font-weight: 400;' + os.linesep + \
                           '}' + os.linesep + \
                           'h1, h2 { margin: 10px 5px 10px 5px; }' + os.linesep + \
                           'h1 { font-size: 28px; }' + os.linesep + \
                           'h2 { font-size: 22px;}' + os.linesep + \
                           'h3 { font-size: 18px; }' + os.linesep + \
                           'p, ol, blockquote, h3, table, pre { margin: 1px 20px 2px 7px; }' + os.linesep + \
                           'table, th, td, pre { border: 1px solid gray; border-spacing: 0px; }' + os.linesep + \
                           'table { width: 100%; }' + os.linesep + \
                           'th, td { padding: 1px; }' + os.linesep + \
                           'pre { padding: 4px; }' + os.linesep + \
                           '.checksum { font-size: 12px; }' + os.linesep + \
                           '</style>' + os.linesep + \
                           '</head>' + os.linesep + \
                           '<body>' + os.linesep
        self.html_footer = '</body>' + os.linesep + \
                           '</html>' + os.linesep

    def _logo(self):
        logo = _make_path(self.sbpath, options.basepath, 'images',
                          'rtemswhitebg.jpg')
        try:
            with open(logo, "rb") as image:
                b64 = base64.b64encode(image.read())
        except:
            raise error.general('installation error: no logo found')
        logo = '<img alt="RTEMS Project" height="100" src="data:image/png;base64,' + b64 + '" />'
        return logo

    def format(self):
        return 'html'

    def ext(self):
        return '.html'

    def introduction(self, name, now, intro_text):
        self.name = name
        self.now = now
        super(html_formatter, self).introduction(name, now, intro_text)

    def post_process(self):
        try:
            import markdown
        except:
            raise error.general('installation error: no markdown found')
        try:
            out = markdown.markdown(self.content,
                                    output_format='html5',
                                    extensions=[
                                        'markdown.extensions.toc',
                                        'markdown.extensions.tables',
                                        'markdown.extensions.sane_lists',
                                        'markdown.extensions.smarty'
                                    ])
        except:
            raise
            raise error.general('application error: markdown failed')
        header = self.html_header.replace('@BUILD@', self.name).replace(
            '@NOW@', self.now)
        footer = self.html_footer
        logo = self._logo()
        return header + logo + out + footer


class text_formatter(formatter):

    def __init__(self):
        super(text_formatter, self).__init__()
        self.cini = ''

    def format(self):
        return 'text'

    def ext(self):
        return '.txt'

    def introduction(self, name, now, intro_text):
        self.line('=' * _line_len)
        self.line('%s %s' % (_title, now))
        if intro_text:
            self.line('')
            self.line('%s' % ('\n'.join(intro_text)))
        self.line('=' * _line_len)
        self.line('Report: %s' % (name))

    def release_status_header(self):
        self.line('-' * _line_len)
        self.line('%s' % (_release_status_text))

    def release_status(self, release_string):
        self.release_status_header()
        self.line('%s Version: %s' % (self.cini, release_string))

    def git_status_header(self):
        self.line('-' * _line_len)
        self.line('%s' % (_git_status_text))

    def git_status(self, valid, dirty, head, remotes):
        self.git_status_header()
        if valid:
            self.line('%s Remotes:' % (self.cini))
            rc = 0
            if not remotes:
                self.line('[ remotes removed, contact sender for details ]')
            else:
                for r in remotes:
                    rc += 1
                    if 'url' in remotes[r]:
                        text = remotes[r]['url']
                    else:
                        text = 'no URL found'
                    text = '%s: %s' % (r, text)
                    self.line('%s  %2d: %s' % (self.cini, rc, text))
            self.line('%s Status:' % (self.cini))
            if dirty:
                self.line('%s  Repository is dirty' % (self.cini))
            else:
                self.line('%s  Clean' % (self.cini))
            self.line('%s Head:' % (self.cini))
            self.line('%s  Commit: %s' % (self.cini, head))
        else:
            self.line('%s Not a valid GIT repository' % (self.cini))


class ini_formatter(text_formatter):

    def __init__(self):
        super(ini_formatter, self).__init__()
        self.cini = ';'
        self.ini_pkg = {}
        self.name = None

    def format(self):
        return 'ini'

    def ext(self):
        return '.ini'

    def introduction(self, name, now, intro_text):
        self.line(';')
        self.line('; %s %s' % (_title, now))
        if intro_text:
            self.line(';')
            self.line('; %s' % ('\n; '.join(intro_text)))
            self.line(';')

    def epilogue(self, name):
        pkgs = sorted(self.ini_pkg.keys())
        for pkg in pkgs:
            self.line('')
            self.line('[%s]' % (pkg))
            items = sorted(self.ini_pkg[pkg].keys())
            for item in items:
                i = self.ini_pkg[pkg][item]
                if len(i) == 1:
                    self.line('%s = "%s"' % (item, i[0]))
                else:
                    self.line('%s = <<<DATA' % (item))
                    self.line('\n'.join(i))
                    self.line('DATA')
        self.line('')

    def release_status_header(self):
        self.line(';')
        self.line('; %s' % (_release_status_text))

    def git_status_header(self):
        self.line(';')
        self.line('; %s' % (_git_status_text))
        self.line(';')

    def config(self, nest_level, name, _config):
        pass

    def buildset_start(self, nest_level, name):
        if name.endswith('.cfg'):
            self.name = path.basename(name[:-4])
            if self.name not in self.ini_pkg:
                self.ini_pkg[self.name] = {}

    def buildset_end(self, nest_level, name):
        self.name = None

    def info(self, nest_level, name, info, separated):
        if self.name:
            if 'info' not in self.ini_pkg[self.name]:
                self.ini_pkg[self.name]['info'] = []
            self.ini_pkg[self.name]['info'] += info

    def directive(self, nest_level, name, data):
        if self.name:
            if name not in self.ini_pkg[self.name]:
                self.ini_pkg[self.name][name] = []
            self.ini_pkg[self.name][name] += data

    def files(self, nest_level, singular, plural, _files):
        pass


class xml_formatter(formatter):

    def __init__(self):
        super(xml_formatter, self).__init__()

    def format(self):
        return 'xml'

    def ext(self):
        return '.xml'

    def introduction(self, name, now, intro_text):
        self.line('<RTEMSSourceBuilderReport>')
        if intro_text:
            self.line('\t<Introduction>%s</Introduction>' % (intro_text))

    def epilogue(self, name):
        self.line('</RTEMSSourceBuilderReport>')

    def release_status(self, release_string):
        self.line('\t<Release>')
        self.line('\t\t<Version>%s</Version>' % (release_string))
        self.line('\t</Release>')

    def git_status(self, valid, dirty, head, remotes):
        self.line('\t<Git>')
        if valid:
            if dirty:
                self.line('\t\t<Status>dirty</Status>')
            else:
                self.line('\t\t<Status>clean</Status>')
            self.line('\t\t<Commit>' + head + '</Commit>')
        else:
            self.line('\t\t<Status>invalid</Status>')
        self.line('\t</Git>')

    def config_start(self, nest_level, name):
        self.line('\t' * nest_level + '<Package name="' + name + '">')

    def config(self, nest_level, name, _config):
        self.line('\t' * nest_level + '<Config>' + _config.file_name() +
                  '</Config>')

    def config_end(self, nest_level, name):
        self.line('\t' * nest_level + '</Package>')

    def buildset_start(self, nest_level, name):
        self.line('\t' * nest_level + '<BuildSet name="' + name + '">')

    def buildset_end(self, nest_level, name):
        self.line('\t' * nest_level + '</BuildSet>')

    def info(self, nest_level, name, info, separated):
        self.add('\t' * nest_level + '<' + name.replace(' ', '') + '>')
        for l in info:
            self.add(l)
        self.line('</' + name + '>')

    def directive(self, nest_level, name, data):
        self.line('\t' * nest_level + '<' + name + '><![CDATA[')
        for l in data:
            self.line(l.replace(']]>', ']]]><![CDATA[]>'))
        self.line(']]></' + name + '>')

    def files(self, nest_level, sigular, plural, _files):
        for name in _files:
            for s in _files[name]:
                self.add('\t' * nest_level + '<' + sigular)
                if not (s[1] is None):
                    hash = s[1].split()
                    self.add(' ' + hash[0] + '="' + hash[1] + '"')
                self.line('>' + s[0] + '</' + sigular + '>')


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

    def __init__(self, formatter, sanitize, _configs, opts, macros=None):
        if type(formatter) == str:
            if formatter == 'text':
                self.formatter = text_formatter()
            elif formatter == 'markdown':
                self.formatter = markdown_formatter()
            elif formatter == 'html':
                self.formatter = html_formatter()
            elif formatter == 'ini':
                self.formatter = ini_formatter()
            elif formatter == 'xml':
                self.formatter = xml_formatter()
            else:
                raise error.general('invalid format: %s' % (formatter))
        else:
            self.formatter = formatter
        self.configs = _configs
        self.opts = opts
        self.sanitize = sanitize
        if macros is None:
            self.macros = opts.defaults
        else:
            self.macros = macros
        self.sbpath = self.macros.expand('%{_sbdir}')
        self.formatter.set_sbpath(self.sbpath)
        self.bset_nesting = 0
        self.out = ''
        self.tree = {}
        self.files = {'buildsets': [], 'configs': []}

    def output(self, text):
        self.formatter.line(text)

    def is_ini(self):
        return self.formatter.format() == 'ini'

    def header(self):
        pass

    def footer(self):
        pass

    def release_status(self):
        self.formatter.release_status(version.string())

    def git_status(self):
        r = git.repo('.', self.opts, self.macros)
        if self.sanitize:
            self.formatter.git_status(r.valid(), r.dirty(), r.head(), None)
        else:
            self.formatter.git_status(r.valid(), r.dirty(), r.head(),
                                      r.remotes())

    def introduction(self, name, intro_text=None):
        now = datetime.datetime.now().ctime()
        self.formatter.introduction(name, now, intro_text)
        if version.released():
            self.release_status()
        else:
            self.git_status()

    def epilogue(self, name):
        self.formatter.epilogue(name)

    def config_start(self, name, _config):
        self.files['configs'] += [name]
        for cf in _config.includes():
            cfbn = path.basename(cf)
            if cfbn not in self.files['configs']:
                self.files['configs'] += [cfbn]
        self.formatter.config_start(self.bset_nesting + 1, name)

    def config_end(self, name, _config):
        self.formatter.config_end(self.bset_nesting + 1, name)

    def buildset_start(self, name):
        self.bset_nesting += 1
        self.files['buildsets'] += [name]
        self.formatter.buildset_start(self.bset_nesting, name)

    def buildset_end(self, name):
        self.formatter.buildset_end(self.bset_nesting, name)
        self.bset_nesting -= 1

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
            srcs[p] = [(s, sources.get_hash(path.basename(s).lower(), macros))
                       for s in _srcs[p]]
        return srcs

    def patch(self, macros):

        def err(msg):
            raise error.general('%s' % (msg))

        _patches = {}
        for n in sources.get_patch_names(macros, err):
            if 'setup' in sources.get_patch_keys(n, macros, err):
                _patches[n] = \
                    [p for p in sources.get_patches(n, macros, err) if not p.startswith('%setup')]
                _patches[n] = [
                    macros.expand(p.split()[-1]) for p in _patches[n]
                ]
        patches = {}
        for n in _patches:
            patches[n] = [(p,
                           sources.get_hash(path.basename(p).lower(), macros))
                          for p in _patches[n]]
        return patches

    def output_info(self, name, info, separated=False):
        if info is not None:
            self.formatter.info(self.bset_nesting + 2, name, info, separated)

    def output_directive(self, name, directive):
        if directive is not None:
            self.formatter.directive(self.bset_nesting + 2, name, directive)

    def tree_packages(self, tree, packages=[]):
        if 'bset' in tree:
            for node in sorted(tree['bset'].keys()):
                packages += [_tree_name(node)]
                packages += self.tree_packages(tree['bset'][node], packages)
        return set(packages)

    def tree_sources(self, name, tree, sources=[]):
        if 'cfg' in tree:
            packages = {}
            if 'sources' in tree['cfg']:
                _merge(packages, tree['cfg']['sources'])
            if 'patches' in tree['cfg']:
                _merge(packages, tree['cfg']['patches'])
            for package in packages:
                for source in packages[package]:
                    if not source[0].startswith(
                            'git') and not source[0].startswith('cvs'):
                        sources += [(path.basename(source[0]), source[0],
                                     source[1])]
        if 'bset' in tree:
            for node in sorted(tree['bset'].keys()):
                self.tree_sources(_tree_name(node), tree['bset'][node],
                                  sources)
        return sources

    def config(self, _config, tree, opts, macros):
        packages = _config.packages()
        package = packages['main']
        name = package.name()
        if len(name) == 0:
            return
        sources = self.source(macros)
        patches = self.patch(macros)
        if tree is not None:
            tree['file'] += [_config.file_name()]
            if len(sources):
                if 'sources' in tree:
                    tree['sources'] = dict(
                        list(tree['sources'].items()) + list(sources.items()))
                else:
                    tree['sources'] = sources
            if len(patches):
                if 'patches' in tree:
                    tree['patches'] = dict(
                        list(tree['patches'].items()) + list(patches.items()))
                else:
                    tree['patches'] = patches
        self.config_start(name, _config)
        self.formatter.config(self.bset_nesting + 2, name, _config)
        self.output_info('Summary', package.get_info('summary'), True)
        self.output_info('URL', package.get_info('url'))
        self.output_info('Version', package.get_info('version'))
        self.output_info('Release', package.get_info('release'))
        self.output_info('Build Arch', package.get_info('buildarch'))
        self.formatter.files(self.bset_nesting + 2, "Source", "Sources",
                             sources)
        self.formatter.files(self.bset_nesting + 2, "Patch", "Patches",
                             patches)
        self.output_directive('Preparation', package.prep())
        self.output_directive('Build', package.build())
        self.output_directive('Install', package.install())
        self.output_directive('Clean', package.clean())
        self.config_end(name, _config)

    def generate_ini_tree(self, name, tree, prefix_char, prefix=''):
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
                if 'bset' in tree and len(list(tree['bset'].keys())):
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
                self.generate_ini_tree(nodes[node], tree['bset'][nodes[node]],
                                       prefix_char, prefix)

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
        nodes = sorted(
            [node for node in list(self.tree.keys()) if node != 'bset'])
        self.output(';')
        self.output('; Configuration Tree:')
        for node in range(0, len(nodes)):
            if node == len(nodes) - 1:
                prefix_char = ' '
            else:
                prefix_char = '|'
            self.generate_ini_tree(nodes[node], self.tree[nodes[node]],
                                   prefix_char)
        self.output(';')
        sources = []
        for node in nodes:
            sources += self.tree_sources(_tree_name(node), self.tree[node])
        sources = sorted(set(sources))
        self.generate_ini_source(sources)
        self.generate_ini_hash(sources)

    def get_output(self):
        return self.formatter.post_process()

    def write(self, name):
        self.out = self.formatter.post_process()
        if name is not None:
            try:
                o = open(path.host(name), "w")
                o.write(self.out)
                o.close()
                del o
            except IOError as err:
                raise error.general('writing output file: %s: %s' %
                                    (name, err))

    def generate(self, name, tree=None, opts=None, macros=None):
        from . import setbuilder
        self.buildset_start(name)
        if tree is None:
            tree = self.tree
        if opts is None:
            opts = self.opts
        if macros is None:
            macros = self.macros
        bset = setbuilder.buildset(name, self.configs, opts, macros)
        if name in tree:
            raise error.general('duplicate build set in tree: %s' % (name))
        tree[name] = {'bset': {}, 'cfg': {'file': []}}
        for c in bset.load():
            macros = copy.copy(bset.macros)
            if c.endswith('.bset'):
                self.generate(c, tree[name]['bset'], bset.opts, macros)
            elif c.endswith('.cfg'):
                self.buildset_start(c)
                self.config(config.file(c, bset.opts, macros),
                            tree[name]['cfg'], bset.opts, macros)
                self.buildset_end(c)
            else:
                raise error.general('invalid config type: %s' % (c))
        self.buildset_end(name)

    def create(self, inname, outname=None, intro_text=None):
        self.introduction(inname, intro_text)
        self.generate(inname)
        if self.is_ini():
            self.generate_ini()
        self.epilogue(inname)
        self.write(outname)


def run(args):
    try:
        from . import setbuilder
        optargs = {
            '--list-bsets': 'List available build sets',
            '--list-configs': 'List available configurations',
            '--format': 'Output format (text, html, markdown, ini, xml)',
            '--output': 'File name to output the report',
            '--sanitize': 'Remove Remotes information from report'
        }
        opts = options.load(args, optargs, logfile=False)
        if opts.get_arg('--output') and len(opts.params()) > 1:
            raise error.general(
                '--output can only be used with a single config')
        print('RTEMS Source Builder, Reporter, %s' % (version.string()))
        opts.log_info()
        if not check.host_setup(opts):
            log.warning('forcing build with known host setup problems')
        configs = build.get_configs(opts)
        if not setbuilder.list_bset_cfg_files(opts, configs):
            output = opts.get_arg('--output')
            if output is not None:
                output = output[1]
            formatter = text_formatter()
            format_opt = opts.get_arg('--format')
            if format_opt:
                if len(format_opt) != 2:
                    raise error.general('invalid format option: %s' %
                                        ('='.join(format_opt)))
                if format_opt[1] == 'text':
                    pass
                elif format_opt[1] == 'markdown':
                    formatter = markdown_formatter()
                elif format_opt[1] == 'html':
                    formatter = html_formatter()
                elif format_opt[1] == 'ini':
                    formatter = ini_formatter()
                elif format_opt[1] == 'xml':
                    formatter = xml_formatter()
                else:
                    raise error.general('invalid format: %s' % (format_opt[1]))
            sanitize = False
            if opts.get_arg('--sanitize'):
                sanitize = True
            r = report(formatter, sanitize, configs, opts)
            for _config in opts.params():
                if output is None:
                    outname = path.splitext(_config)[0] + formatter.ext()
                    outname = outname.replace('/', '-')
                else:
                    outname = output
                config = build.find_config(_config, configs)
                if config is None:
                    raise error.general('config file not found: %s' %
                                        (_config))
                r.create(config, outname)
            del r
    except error.general as gerr:
        print(gerr)
        sys.exit(1)
    except error.internal as ierr:
        print(ierr)
        sys.exit(1)
    except error.exit as eerr:
        pass
    except KeyboardInterrupt:
        log.notice('abort: user terminated')
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    run(sys.argv)
