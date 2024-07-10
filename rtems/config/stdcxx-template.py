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
