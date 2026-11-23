"""Stage experiment inputs and checkpoint one local Colab run to mounted Drive."""

import json
import os
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path


def copy_tree_once(source, target):
    """Publish a complete directory, or reuse the already published copy."""
    if target.exists() or not source.is_dir():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=".staging-") as tmp:
        staged = Path(tmp) / "tree"
        shutil.copytree(source, staged, ignore=shutil.ignore_patterns(".staging-*", ".lock"))
        staged.rename(target)


def copy_file(source, target, contents=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".staging-", delete=False) as f:
        tmp = Path(f.name)
    try:
        if contents is None:
            shutil.copy2(source, tmp)
        else:
            tmp.write_bytes(contents)
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)


def save_data(source, target):
    # Readers use the manifest to decide which dataset files are complete.
    for path in sorted(source.glob("*.jsonl")):
        copy_file(path, target / path.name)
    copy_file(source / "manifest.json", target / "manifest.json")


def sync_results(source, target):
    """Append complete JSONL records only, repairing a torn last Drive write."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as local, target.open("a+b") as backup:
        end = backup.tell()
        while end:
            start = max(0, end - 65536)
            backup.seek(start)
            newline = backup.read(end - start).rfind(b"\n")
            if newline >= 0:
                end = start + newline + 1
                break
            end = start
        if end > source.stat().st_size:
            raise RuntimeError("Drive results are ahead of local results. Check for another session.")
        backup.truncate(end)
        local.seek(end)
        for line in local:
            if line.endswith(b"\n"):
                backup.write(line)
        backup.flush()
        os.fsync(backup.fileno())


class RunBackup:
    def __init__(self, local, drive):
        self.local = local
        self.drive = drive
        self.saved = {}
        self.adapters = set()

    def sync(self):
        if not self.local.exists():
            return
        for path in sorted(self.local.iterdir()):
            if path.name.startswith(".") or not path.is_file():
                continue
            stat = path.stat()
            stamp = (stat.st_size, stat.st_mtime_ns)
            if self.saved.get(path) == stamp:
                continue
            target = self.drive / path.name
            if path.name == "results.jsonl":
                sync_results(path, target)
            else:
                contents = None
                if path.suffix == ".json":
                    contents = path.read_bytes()
                    try:
                        json.loads(contents)
                    except ValueError:
                        continue  # The runner is still writing this file.
                copy_file(path, target, contents)
            self.saved[path] = stamp
        for marker in (self.local / "adapters").glob("*/complete.json"):
            adapter = marker.parent
            if adapter in self.adapters:
                continue
            target = self.drive / "adapters" / adapter.name
            if not (target / marker.name).exists():
                contents = marker.read_bytes()
                try:
                    json.loads(contents)
                except ValueError:
                    continue
                # Older direct-to-Drive runs can contain unfinished adapters.
                for path in adapter.iterdir():
                    if path.is_file() and path != marker:
                        copy_file(path, target / path.name)
                copy_file(marker, target / marker.name, contents)
            self.adapters.add(adapter)

    def run(self, args, env, cwd, interval=60):
        process = subprocess.Popen(args, env=env, cwd=cwd, start_new_session=True)
        try:
            while True:
                try:
                    status = process.wait(timeout=interval)
                except subprocess.TimeoutExpired:
                    self.sync()
                    continue
                if status:
                    raise subprocess.CalledProcessError(status, args)
                break
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            self.sync()
