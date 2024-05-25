#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2019 Chris Johns (chrisj@rtems.org)
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

try:
    from . import error
    from . import execute
    from . import log
    from . import options
except KeyboardInterrupt:
    print('abort: user terminated', file=sys.stderr)
    sys.exit(1)
except:
    raise


def expand(macros, line):
    #
    # Parse the line and handle nesting '()' pairs.
    #
    def _exec(shell_macro):
        output = ''
        if len(shell_macro) > 3:
            e = execute.capture_execution()
            if options.host_windows:
                cmd = '%s -c "%s"' % (macros.expand('%{__sh}'),
                                      shell_macro[2:-1])
            else:
                cmd = shell_macro[2:-1]
            exit_code, proc, output = e.shell(cmd)
            log.trace('shell-output: %d %s' % (exit_code, output))
            if exit_code != 0:
                raise error.general('shell macro failed: %s: %d: %s' %
                                    (cmd, exit_code, output))
        return output

    updating = True
    while updating:
        updating = False
        pos = line.find('%(')
        if pos >= 0:
            braces = 0
            for p in range(pos + 2, len(line)):
                if line[p] == '(':
                    braces += 1
                elif line[p] == ')':
                    if braces > 0:
                        braces -= 1
                    else:
                        line = line[:pos] + _exec(
                            line[pos:p + 1]) + line[p + 1:]
                        updating = True
                        break
    return line
