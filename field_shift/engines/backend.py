"""Array module selection: CuPy on a CUDA GPU when available, NumPy otherwise."""

from __future__ import annotations

import numpy as np


def gpu_module():
    """CuPy if it is installed and a device answers, else None."""
    try:
        import cupy
        cupy.cuda.runtime.getDeviceCount()
        cupy.zeros(1).sum()
        return cupy
    except Exception:  # missing package, driver or device
        return None


def array_module(device: str = "auto"):
    """`device` is 'auto', 'gpu' or 'cpu'. 'gpu' fails loudly when there is no GPU."""
    if device == "cpu":
        return np
    module = gpu_module()
    if module is None and device == "gpu":
        raise RuntimeError("no CUDA GPU available (install the 'gpu' extra and check the driver)")
    return module or np


def to_numpy(array) -> np.ndarray:
    return array.get() if hasattr(array, "get") else np.asarray(array)


def streams(xp, seed: int, names: tuple[str, ...]) -> dict:
    """One independent generator per name, all derived from `seed`. The same seed gives the same streams."""
    children = np.random.SeedSequence(seed).spawn(len(names))
    return {name: xp.random.default_rng(int(child.generate_state(1)[0])) for name, child in zip(names, children)}
