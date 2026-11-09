"""Command-line entry point for the isolated stress-testing utility."""
from __future__ import annotations

import argparse
import asyncio
import json
import signal
import sys
from pathlib import Path

from .config import load_config
from .engine import StressTestEngine


async def _run(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config, allow_external_target=args.allow_external_target)
    except (OSError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    engine = StressTestEngine(config)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, engine.stop)
        except NotImplementedError:
            pass
    print(f"Target: {config.base_url} | duration: {config.duration}s | concurrency: {config.concurrency}")
    result = await engine.run()
    output = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if result["failed_requests"] == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe, bounded HTTP load testing (GET/HEAD only)")
    parser.add_argument("--config", default="config/stress-test.example.yaml", help="YAML configuration path")
    parser.add_argument("--output", help="Optional JSON results file")
    parser.add_argument("--allow-external-target", action="store_true",
                        help="Allow a non-loopback target; use only with explicit authorization")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
