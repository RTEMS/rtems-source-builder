#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2013-2016 Chris Johns (chrisj@rtems.org)
# Copyright (C) 2021 On-Line Applications Research Corporation (OAR)
# All rights reserved.
#
# This file is part of the RTEMS Tools package in 'rtems-tools'.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

#
# Manage emailing results or reports.
#

from __future__ import print_function

import os
import smtplib
import socket

from . import error
from . import execute
from . import options
from . import path

_options = {
    '--mail'         : 'Send email report or results.',
    '--use-gitconfig': 'Use mail configuration from git config.',
    '--mail-to'      : 'Email address to send the email to.',
    '--mail-from'    : 'Email address the report is from.',
    '--smtp-host'    : 'SMTP host to send via.',
    '--smtp-port'    : 'SMTP port to send via.',
    '--smtp-user'    : 'User for SMTP authentication.',
    '--smtp-password': 'Password for SMTP authentication.'
}

def append_options(opts):
    for o in _options:
        opts[o] = _options[o]

def add_arguments(argsp):
    argsp.add_argument('--mail', help = _options['--mail'], action = 'store_true')
    argsp.add_argument('--use-gitconfig', help = _options['--use-gitconfig'], action = 'store_true')
    no_add = ['--mail', '--use-gitconfig']
    for o in [opt for opt in list(_options) if opt not in no_add]:
        argsp.add_argument(o, help = _options[o], type = str)

class mail:
    def __init__(self, opts):
        self.opts = opts
        self.gitconfig_lines = None
        if opts.find_arg('--use-gitconfig') is not None:
            # Read the output of `git config --list` instead of reading the
            # .gitconfig file directly because Python 2 ConfigParser does not
            # accept tabs at the beginning of lines.
            e = execute.capture_execution()
            exit_code, proc, output = e.open('git config --list', shell=True)
            if exit_code == 0:
                self.gitconfig_lines = output.split(os.linesep)

    def _args_are_macros(self):
        return isinstance(self.opts, options.command_line)

    def _get_arg(self, arg):
        if self._args_are_macros():
            value = self.opts.find_arg(arg)
            if value is not None:
                value = self.opts.find_arg(arg)[1]
        else:
            if arg.startswith('--'):
                arg = arg[2:]
            arg = arg.replace('-', '_')
            if arg in vars(self.opts):
                value = vars(self.opts)[arg]
            else:
                value = None
        return value

    def _get_from_gitconfig(self, variable_name):
        if self.gitconfig_lines is None:
            return None

        for line in self.gitconfig_lines:
            if line.startswith(variable_name):
                ls = line.split('=')
                if len(ls) >= 2:
                    return ls[1]

    def from_address(self):

        def _clean(l):
            if '#' in l:
                l = l[:l.index('#')]
            if '\r' in l:
                l = l[:l.index('r')]
            if '\n' in l:
                l = l[:l.index('\n')]
            return l.strip()

        addr = self._get_arg('--mail-from')
        if addr is not None:
            return addr
        addr = self._get_from_gitconfig('user.email')
        if addr is not None:
            name = self._get_from_gitconfig('user.name')
            if name is not None:
                addr = '%s <%s>' % (name, addr)
            return addr
        mailrc = None
        if 'MAILRC' in os.environ:
            mailrc = os.environ['MAILRC']
        if mailrc is None and 'HOME' in os.environ:
            mailrc = path.join(os.environ['HOME'], '.mailrc')
        if mailrc is not None and path.exists(mailrc):
            # set from="Joe Blow <joe@blow.org>"
            try:
                with open(mailrc, 'r') as mrc:
                    lines = mrc.readlines()
            except IOError as err:
                raise error.general('error reading: %s' % (mailrc))
            for l in lines:
                l = _clean(l)
                if 'from' in l:
                    fa = l[l.index('from') + len('from'):]
                    if '=' in fa:
                        addr = fa[fa.index('=') + 1:].replace('"', ' ').strip()
            if addr is not None:
                return addr
        if self._args_are_macros():
            addr = self.opts.defaults.get_value('%{_sbgit_mail}')
        else:
            raise error.general('no valid from address for mail')
        return addr

    def smtp_host(self):
        host = self._get_arg('--smtp-host')
        if host is not None:
            return host
        host = self._get_from_gitconfig('sendemail.smtpserver')
        if host is not None:
            return host
        if self._args_are_macros():
            host = self.opts.defaults.get_value('%{_mail_smtp_host}')
        if host is not None:
            return host
        return 'localhost'

    def smtp_port(self):
        port = self._get_arg('--smtp-port')
        if port is not None:
            return port
        port = self._get_from_gitconfig('sendemail.smtpserverport')
        if port is not None:
            return port
        if self._args_are_macros():
            port = self.opts.defaults.get_value('%{_mail_smtp_port}')
        return port

    def smtp_user(self):
        user = self._get_arg('--smtp-user')
        if user is not None:
            return user
        user = self._get_from_gitconfig('sendemail.smtpuser')
        return user

    def smtp_password(self):
        password = self._get_arg('--smtp-password')
        if password is not None:
            return password
        password = self._get_from_gitconfig('sendemail.smtppass')
        return password

    def send(self, to_addr, subject, body):
        from_addr = self.from_address()
        msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n" % \
            (from_addr, to_addr, subject) + body
        port = self.smtp_port()

        try:
            s = smtplib.SMTP(self.smtp_host(), port, timeout=10)

            password = self.smtp_password()
            # If a password is provided, assume that authentication is required.
            if password is not None:
                user = self.smtp_user()
                if user is None:
                    user = from_addr
                s.starttls()
                s.login(user, password)

            s.sendmail(from_addr, [to_addr], msg)
        except smtplib.SMTPException as se:
            raise error.general('sending mail: %s' % (str(se)))
        except socket.error as se:
            raise error.general('sending mail: %s' % (str(se)))

    def send_file_as_body(self, to_addr, subject, name, intro = None):
        try:
            with open(name, 'r') as f:
                body = f.readlines()
        except IOError as err:
            raise error.general('error reading mail body: %s' % (name))
        if intro is not None:
            body = intro + body
        self.send(to_addr, from_addr, body)

if __name__ == '__main__':
    import sys
    from . import macros
    optargs = {}
    rtdir = 'source-builder'
    defaults = '%s/defaults.mc' % (rtdir)
    append_options(optargs)
    opts = options.command_line(base_path = '.',
                                argv = sys.argv,
                                optargs = optargs,
                                defaults = macros.macros(name = defaults, rtdir = rtdir),
                                command_path = '.')
    options.load(opts)
    m = mail(opts)
    print('From: %s' % (m.from_address()))
    print('SMTP Host: %s' % (m.smtp_host()))
    if '--mail' in sys.argv:
        m.send(m.from_address(), 'Test mailer.py', 'This is a test')
