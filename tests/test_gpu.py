from final_project import gpu


def test_replica_admission():
    gib = 2**30
    assert gpu.replica_count(4, 8, 4 * gib, 1 * gib) == 1
    assert gpu.replica_count(4, 8, 4 * gib, 0) == 1
    assert gpu.replica_count(4, 8, 4 * gib, 12 * gib) == 2
    assert gpu.replica_count(4, 2, 4 * gib, 80 * gib) == 2
    assert gpu.replica_count(1, 8, 4 * gib, 80 * gib) == 1
    assert gpu.replica_count(4, 8, 4 * gib, 80 * gib, 99, utilization_source="ioreg") == 4
    assert gpu.replica_count(4, 8, 4 * gib, 80 * gib, 99, utilization_source="nvidia-smi") == 1


def test_nvidia_measurement_uses_visible_gpu(monkeypatch):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "GPU-uuid,2")

    def read(*args):
        assert args[2] == "GPU-uuid"
        return "65, 24000"

    monkeypatch.setattr(gpu, "_read", read)
    assert gpu.nvidia_stats() == (65, 24000 * 2**20)


def test_resource_summary_counts_both_turns():
    from final_project.report import summarize

    first = {"mlx_peak_bytes": 10**9, "samples": 2, "device_utilization_mean_pct": 60}
    second = {"mlx_peak_bytes": 2 * 10**9, "samples": 1, "device_utilization_mean_pct": 90}
    row = {
        "benchmark": "gpqa",
        "condition": "icl",
        "n": 2,
        "seed": 0,
        "passed": False,
        "gpu": first,
        "seconds": 3,
        "followup": {"gpu": second, "seconds": 1},
        "generation_workers": 2,
    }
    (group,) = summarize([row])
    assert group["device_utilization_mean_pct"] == 70
    assert group["worker_peak_mlx_gb"] == 2
    assert group["generation_seconds"] == 4
    assert group["max_generation_workers"] == 2
