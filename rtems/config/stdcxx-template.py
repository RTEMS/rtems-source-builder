# SPDX-License-Identifier: BSD-2-Clause

# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2024-2024 Suraj Kumar 
# All rights reserved.

# This package is part of the RTEMS Tools Project.

# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.

# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


import sys
import traceback
import gdb
import os


gdb_path = gdb.PYTHONDIR
gcc_version = "@RSB_GCC_VERSION@"

gcc_path = os.path.dirname(os.path.dirname(gdb_path))
gcc_path = os.path.join(gcc_path, "gcc-" + gcc_version)
gcc_python_path = os.path.join(gcc_path, "python")

sys.path.insert(0, gcc_python_path)

try:
    from libstdcxx.v6.printers import register_libstdcxx_printers
    register_libstdcxx_printers(None)
except Exception as e:
    print(f"Exception during execution: {e}")
    traceback.print_exc()
