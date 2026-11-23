"""Run a HumanEval candidate inside a read-only stdlib chroot on Linux Colab."""

import ctypes
import ctypes.util
import errno
import os
import resource
import sys
from pathlib import Path


def main():
    root, candidate, timeout = sys.argv[1:]
    code = Path(candidate).read_bytes()
    if os.geteuid() != 0:
        raise RuntimeError("Colab code scoring requires permission to chroot and drop privileges")
    library = ctypes.util.find_library("seccomp")
    if not library:
        raise RuntimeError("Install libseccomp2 before scoring")
    sec = ctypes.CDLL(library)
    sec.seccomp_init.argtypes = [ctypes.c_uint32]
    sec.seccomp_init.restype = ctypes.c_void_p
    sec.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    sec.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    sec.seccomp_load.argtypes = [ctypes.c_void_p]
    rules = sec.seccomp_init(0x00050000 | errno.EPERM)
    if not rules:
        raise RuntimeError("seccomp_init failed")
    allowed = [
        "read",
        "write",
        "writev",
        "close",
        "fstat",
        "newfstatat",
        "statx",
        "lseek",
        "openat",
        "getdents64",
        "readlink",
        "readlinkat",
        "getcwd",
        "access",
        "faccessat",
        "mmap",
        "mremap",
        "munmap",
        "mprotect",
        "brk",
        "madvise",
        "futex",
        "clock_gettime",
        "gettimeofday",
        "getrandom",
        "getpid",
        "gettid",
        "rt_sigaction",
        "rt_sigprocmask",
        "rt_sigreturn",
        "sigaltstack",
        "exit",
        "exit_group",
        "fcntl",
        "ioctl",
        "pread64",
        "uname",
        "getrusage",
        "sched_yield",
    ]
    for name in allowed:
        number = sec.seccomp_syscall_resolve_name(name.encode())
        if number >= 0 and sec.seccomp_rule_add(rules, 0x7FFF0000, number, 0):
            raise RuntimeError("Failed to configure seccomp")
    for kind, limit in [
        (resource.RLIMIT_CPU, int(timeout)),
        (resource.RLIMIT_FSIZE, 1048576),
        (resource.RLIMIT_AS, 512 << 20),
        (resource.RLIMIT_CORE, 0),
    ]:
        resource.setrlimit(kind, (limit, limit))
    os.chroot(root)
    os.chdir("/")
    os.setgroups([])
    os.setgid(65534)
    os.setuid(65534)
    sys.path[:] = ["/stdlib", "/stdlib/lib-dynload"]
    os.environ.clear()
    if sec.seccomp_load(rules):
        raise RuntimeError("Failed to activate seccomp")
    exec(compile(code, "candidate.py", "exec"), {"__name__": "__main__"})  # noqa: S102 -- isolated candidate


if __name__ == "__main__":
    main()
