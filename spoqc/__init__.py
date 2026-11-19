from __future__ import annotations

import os as _os

# Cap BLAS/OpenMP threads at the CPUs this process may use (e.g. a SLURM allocation), before
# numpy is imported. Otherwise OpenBLAS sizes itself to all cores of the node and crashes
# ("too many memory regions", segfault) on nodes with more cores than it was built for (>128).
_ncpu = str(len(_os.sched_getaffinity(0)) if hasattr(_os, "sched_getaffinity") else (_os.cpu_count() or 1))
for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    _os.environ.setdefault(_var, _ncpu)

try:
    from importlib.metadata import version as _version
    __version__ = _version("spoqc")
except Exception:  # pragma: no cover
    __version__ = "0.1.0"

__all__ = ["__version__"]