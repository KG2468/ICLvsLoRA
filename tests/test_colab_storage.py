import runpy
from pathlib import Path

storage = runpy.run_path(str(Path(__file__).parents[1] / "scripts/colab_storage.py"))


def test_checkpoint_and_restore(tmp_path):
    local, drive = tmp_path / "local", tmp_path / "drive"
    adapter = local / "adapters/seed0-n16"
    adapter.mkdir(parents=True)
    weights = adapter / "adapters.safetensors"
    weights.write_bytes(b"weights")
    (local / "manifest.json").write_text("{}")
    rows = local / "results.jsonl"
    rows.write_bytes(b'{"i":1}\n{"i":')
    backup = storage["RunBackup"](local, drive)
    backup.sync()
    assert (drive / rows.name).read_bytes() == b'{"i":1}\n'
    assert not (drive / "adapters").exists()

    # Simulate a disconnect during a Drive write, then finish the local row.
    with (drive / rows.name).open("ab") as handle:
        handle.write(b'{"')
    with rows.open("ab") as handle:
        handle.write(b'2}\n')
    (adapter / "complete.json").write_text("{}")
    backup.sync()
    backup.sync()
    restored = tmp_path / "new-vm"
    storage["copy_tree_once"](drive, restored)
    assert (restored / rows.name).read_bytes() == rows.read_bytes()
    assert (restored / weights.relative_to(local)).read_bytes() == b"weights"
    assert (restored / "adapters/seed0-n16/complete.json").is_file()
    # Re-running setup in the same VM must preserve unsnapshotted local rows.
    with (restored / rows.name).open("ab") as handle:
        handle.write(b'{"i":3}\n')
    storage["copy_tree_once"](drive, restored)
    assert (restored / rows.name).read_bytes().endswith(b'{"i":3}\n')
