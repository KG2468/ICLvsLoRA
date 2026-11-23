"""Device-wide samples and conservative capacity estimates for one inference device."""

import os
import re
import subprocess
import sys
import threading


def _read(*command):
    return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL, timeout=3)


def nvidia_stats():
    # Select the first CUDA-visible device, including UUID-based selections.
    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    selector = visible.split(",")[0] if visible is not None else "0"
    rows = (
        _read(
            "nvidia-smi",
            "-i",
            selector,
            "--query-gpu=utilization.gpu,memory.free",
            "--format=csv,noheader,nounits",
        )
        .strip()
        .splitlines()
    )
    if len(rows) != 1:
        raise ValueError("Ambiguous GPU selection")
    utilization, free = rows[0].split(",")
    return (None if "N/A" in utilization else int(utilization)), int(free) * 2**20


def available_bytes():
    try:
        if sys.platform == "darwin":
            import mlx.core as mx

            info = mx.device_info()
            stats = _read("vm_stat")
            page_size = int(re.search(r"page size of (\d+)", stats)[1])
            # Count reclaimable file-backed inactive pages, excluding swap.
            pages = sum(
                int(re.search(rf"Pages {kind}:\s*(\d+)", stats)[1])
                for kind in ("free", "speculative")
            )
            inactive = int(re.search(r"Pages inactive:\s*(\d+)", stats)[1])
            file_backed = int(re.search(r"File-backed pages:\s*(\d+)", stats)[1])
            pages += min(inactive, file_backed)
            return min(
                page_size * pages, info.get("max_recommended_working_set_size", page_size * pages)
            )
        return nvidia_stats()[1]
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        return 0


def replica_count(cap, pending, peak, free, utilization=None, *, utilization_source=None):
    # Called while the pilot model is resident. Keep 2 GiB plus 25% headroom
    # and allow for longer generations and prefix-cache copies in later tasks.
    if not peak or (
        utilization_source == "nvidia-smi" and utilization is not None and utilization >= 95
    ):
        return 1
    extra = max(0, free * 0.75 - 2 * 2**30) // (peak * 1.5)
    return max(1, min(cap, pending, 1 + int(extra)))


class DeviceSamples:
    def __init__(self):
        self.stop = threading.Event()
        self.values = []
        self.source = "ioreg" if sys.platform == "darwin" else "nvidia-smi"
        self.thread = threading.Thread(target=self.collect, daemon=True)

    def collect(self):
        while not self.stop.is_set():
            try:
                if sys.platform == "darwin":
                    output = _read("ioreg", "-r", "-c", "AGXAccelerator", "-l", "-w0")
                    value = int(re.search(r'"Device Utilization %"\s*=\s*(\d+)', output)[1])
                else:
                    value, _ = nvidia_stats()
                if value is not None:
                    self.values.append(value)
            except (OSError, subprocess.SubprocessError, TypeError, ValueError):
                return
            self.stop.wait(1)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join()

    def summary(self):
        return {
            "utilization_source": self.source,
            "samples": len(self.values),
            "device_utilization_mean_pct": sum(self.values) / len(self.values)
            if self.values
            else None,
            "device_utilization_max_pct": max(self.values, default=None),
        }
