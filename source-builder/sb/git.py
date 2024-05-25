#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2016 Chris Johns (chrisj@rtems.org)
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
# Provide some basic access to the git command.
#

from __future__ import print_function

import os

from . import error
from . import execute
from . import log
from . import path


class repo:
    """An object to manage a git repo."""

    def _git_exit_code(self, ec):
        if ec:
            raise error.general('git command failed (%s): %d' % (self.git, ec))

    def _run(self, args, check=False):
        e = execute.capture_execution()
        if path.exists(self.path):
            cwd = self.path
        else:
            cwd = None
        cmd = [self.git] + args
        log.trace('cmd: (%s) %s' % (str(cwd), ' '.join(cmd)))
        exit_code, proc, output = e.spawn(cmd, cwd=path.host(cwd))
        log.trace(output)
        if check:
            self._git_exit_code(exit_code)
        return exit_code, output

    def __init__(self, _path, opts=None, macros=None):
        self.path = _path
        self.opts = opts
        if macros is None and opts is not None:
            self.macros = opts.defaults
        else:
            self.macros = macros
        if self.macros is None:
            self.git = 'git'
        else:
            self.git = self.macros.expand('%{__git}')

    def git_version(self):
        ec, output = self._run(['--version'], True)
        gvs = output.split()
        if len(gvs) < 3:
            raise error.general('invalid version string from git: %s' %
                                (output))
        vs = gvs[2].split('.')
        if len(vs) not in [3, 4]:
            raise error.general('invalid version number from git: %s' %
                                (gvs[2]))
        return tuple(map(int, vs))

    def clone(self, url, _path):
        ec, output = self._run(['clone', url, path.host(_path)], check=True)

    def fetch(self):
        ec, output = self._run(['fetch'], check=True)

    def merge(self):
        ec, output = self._run(['merge'], check=True)

    def pull(self):
        ec, output = self._run(['pull'], check=True)

    def reset(self, args):
        if type(args) == str:
            args = [args]
        ec, output = self._run(['reset'] + args, check=True)

    def branch(self):
        ec, output = self._run(['branch'])
        if ec == 0:
            for b in output.split('\n'):
                if b[0] == '*':
                    return b[2:]
        return None

    def checkout(self, branch='master'):
        ec, output = self._run(['checkout', branch], check=True)

    def submodule(self, module):
        ec, output = self._run(['submodule', 'update', '--init', module],
                               check=True)

    def submodule_foreach(self, args=[]):
        if type(args) == str:
            args = [args.split(args)]
        ec, output = self._run(
            ['submodule', 'foreach', '--recursive', self.git] + args,
            check=True)

    def submodules(self):
        smodules = {}
        ec, output = self._run(['submodule'], check=True)
        if ec == 0:
            for l in output.split('\n'):
                ms = l.split()
                if len(ms) == 3:
                    smodules[ms[1]] = (ms[0], ms[2][1:-1])
        return smodules

    def clean(self, args=[]):
        if type(args) == str:
            args = [args]
        ec, output = self._run(['clean'] + args, check=True)

    def status(self, submodules_always_clean=False):
        _status = {}
        if path.exists(self.path):
            if submodules_always_clean:
                submodules = self.submodules()
            else:
                submodules = {}
            ec, output = self._run(['status'])
            if ec == 0:
                state = 'none'
                for l in output.split('\n'):
                    if l.startswith('# '):
                        l = l[2:]
                    if l.startswith('On branch '):
                        _status['branch'] = l[len('On branch '):]
                    elif l.startswith('Changes to be committed:'):
                        state = 'staged'
                    elif l.startswith('Changes not staged for commit:'):
                        state = 'unstaged'
                    elif l.startswith('Untracked files:'):
                        state = 'untracked'
                    elif l.startswith('HEAD detached'):
                        state = 'detached'
                    elif state != 'none' and len(l.strip()) != 0:
                        if l[0].isspace():
                            l = l.strip()
                            if l[0] != '(':
                                if ':' in l:
                                    l = l.split(':')[1]
                                if len(l.strip()) > 0:
                                    l = l.strip()
                                    ls = l.split()
                                    if state != 'unstaged' or ls[
                                            0] not in submodules:
                                        if state not in _status:
                                            _status[state] = [l]
                                        else:
                                            _status[state] += [l]
        return _status

    def dirty(self):
        _status = self.status()
        _status.pop('untracked', None)
        _status.pop('detached', None)
        return not (len(_status) == 1 and 'branch' in _status)

    def valid(self):
        if path.exists(self.path):
            ec, output = self._run(['status'])
            return ec == 0
        return False

    def remotes(self):
        _remotes = {}
        ec, output = self._run(['config', '--list'])
        if ec == 0:
            for l in output.split('\n'):
                if l.startswith('remote'):
                    ls = l.split('=')
                    if len(ls) >= 2:
                        rs = ls[0].split('.')
                        if len(rs) == 3:
                            r_name = rs[1]
                            r_type = rs[2]
                            if r_name not in _remotes:
                                _remotes[r_name] = {}
                            if r_type not in _remotes[r_name]:
                                _remotes[r_name][r_type] = []
                            _remotes[r_name][r_type] = '='.join(ls[1:])
        return _remotes

    def email(self):
        _email = None
        _name = None
        ec, output = self._run(['config', '--list'])
        if ec == 0:
            for l in output.split('\n'):
                if l.startswith('user.email'):
                    ls = l.split('=')
                    if len(ls) >= 2:
                        _email = ls[1]
                elif l.startswith('user.name'):
                    ls = l.split('=')
                    if len(ls) >= 2:
                        _name = ls[1]
        if _email is not None:
            if _name is not None:
                _email = '%s <%s>' % (_name, _email)
            return _email
        return None

    def head(self):
        hash = ''
        ec, output = self._run(['log', '-n', '1'])
        if ec == 0:
            l1 = output.split('\n')[0]
            if l1.startswith('commit '):
                hash = l1[len('commit '):]
        return hash

    def default_branch(self):
        ec, output = self._run(['remote', 'show'])
        if ec == 0:
            origin = output.split('\n')[0]
            ec, output = self._run(['remote', 'show', origin])
            if ec == 0:
                for l in output.split('\n'):
                    l = l.strip()
                    if l.startswith('HEAD branch: '):
                        return l[len('HEAD branch: '):]
        return None


if __name__ == '__main__':
    import os.path
    import sys
    from . import options
    defaults = path.join(path.dirname(path.dirname(path.shell(sys.argv[0]))),
                         'defaults.mc')
    opts = options.load(sys.argv, defaults=defaults)
    g = repo('.', opts)
    print('g.git_version():', g.git_version())
    print('g.valid():', g.valid())
    print('g.submodules():', g.submodules())
    print('g.status():', g.status())
    print('g.status():', g.status(True))
    print('g.dirty():', g.dirty())
    print('g.remotes():', g.remotes())
    print('g.email():', g.email())
    print('g.head():', g.head())
