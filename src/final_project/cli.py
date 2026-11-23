from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config


def main():
    parser = argparse.ArgumentParser(description="Local MLX LoRA vs persistent ICL experiments")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "model", "plan", "preflight", "run"):
        command = sub.add_parser(name)
        command.add_argument("--config", default="configs/smoke.toml")
        if name == "run":
            command.add_argument(
                "--stage",
                choices=["all", "icl", "lora", "base"],
                default="all",
                help="Default: all ICL, then all LoRA, then base comparisons",
            )
        if name in {"model", "plan", "preflight", "run"}:
            command.add_argument("--precision", choices=["fp16", "fp8", "int8"])
    command = sub.add_parser("report")
    command.add_argument("directory", type=Path)
    command = sub.add_parser("transpile")
    command.add_argument("file", type=Path)
    command.add_argument("--decode", action="store_true")
    command.add_argument("--seed", type=int, default=182)
    command = sub.add_parser("_train", help=argparse.SUPPRESS)
    command.add_argument("job", type=Path)
    args = parser.parse_args()
    if args.command == "report":
        from .report import report

        report(args.directory)
        return
    if args.command == "transpile":
        from .language import Language

        language = Language(args.seed)
        print((language.decode if args.decode else language.encode)(args.file.read_text()), end="")
        return
    if args.command == "_train":
        from .data import examples
        from .language import Language
        from .training import train_adapter

        job = json.loads(args.job.read_text())
        cfg = job["cfg"]
        lang = Language(job["seed"])
        train, valid = examples(cfg, lang, job["seed"])
        train_adapter(cfg, lang, train[: job["n"]], valid, job["seed"], Path(job["adapter"]))
        return
    cfg = load_config(args.config)
    if getattr(args, "precision", None):
        cfg["model"]["precision"] = args.precision
        cfg["experiment"]["name"] += "-" + args.precision
    if args.command == "prepare":
        from .data import prepare

        prepare(cfg)
    elif args.command == "model":
        from .backend import convert

        convert(cfg)
    else:
        from .experiment import plan, preflight, run

        if args.command == "plan":
            print(json.dumps(plan(cfg), indent=2))
        elif args.command == "preflight":
            print(json.dumps(preflight(cfg), indent=2))
        else:
            run(cfg, stage=args.stage)
