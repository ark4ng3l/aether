"""
AETHER — run.py
Unified entry point for Web Dashboard, CLI investigations, Tool executions, and Headless automation.

Usage:
    python run.py --web                              Start FastAPI Dashboard (default)
    python run.py --cli [seed]                       Start interactive CLI or run investigation
    python run.py --scan <target> [--output rep.md]  Headless investigation
    python run.py --tool <name> [--params '{...}']   Run a single Arsenal tool
    python run.py --list-tools                       List all 34 registered tools
    python run.py --config                           Inspect active LLM provider & settings
"""

import argparse
import asyncio
import sys
from pathlib import Path

# ── Path bootstrap ────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
PARENT_DIR = BASE_DIR.parent
for p in (str(BASE_DIR), str(PARENT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


def run_web(host: str = "127.0.0.1", port: int = 8000):
    """Start the FastAPI dashboard with uvicorn."""
    import uvicorn
    print("Starting AETHER Web Dashboard...")
    print(f"  -> http://{host}:{port}")
    uvicorn.run(
        "aether.api.server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


def main():
    parser = argparse.ArgumentParser(
        description="AETHER — Autonomous Cyber-Intelligence & Neural OSINT Engine",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--web", action="store_true", help="Start the FastAPI web dashboard")
    group.add_argument("--cli", nargs="?", const="", metavar="SEED",
                       help="Run interactive CLI or investigate a seed")
    group.add_argument("--scan", metavar="TARGET",
                       help="Run automated investigation on a target")
    group.add_argument("--tool", metavar="TOOL_NAME",
                       help="Execute a specific Arsenal tool directly")
    group.add_argument("--list-tools", action="store_true",
                       help="List all registered OSINT and Reconnaissance tools")
    group.add_argument("--config", action="store_true",
                       help="Display active LLM configuration and model mappings")

    # Modifiers
    parser.add_argument("--params", default="{}", help="JSON parameters for --tool execution")
    parser.add_argument("--depth", type=int, default=None, help="Override maximum search depth")
    parser.add_argument("--output", metavar="FILE", help="Save dossier/report to file")
    parser.add_argument("--format", choices=["md", "json"], default="md", help="Export format")
    parser.add_argument("--host", default="127.0.0.1", help="Web dashboard host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Web dashboard port (default: 8000)")

    args = parser.parse_args()

    from aether.cli.main import (
        cli_scan,
        cli_run_tool,
        cli_list_tools,
        cli_show_config,
        cli_interactive,
    )

    try:
        if args.list_tools:
            cli_list_tools()
        elif args.config:
            cli_show_config()
        elif args.tool:
            asyncio.run(cli_run_tool(args.tool, args.params))
        elif args.scan:
            asyncio.run(cli_scan(
                target=args.scan,
                depth=args.depth,
                output_file=args.output,
                export_format=args.format,
            ))
        elif args.cli is not None:
            if args.cli:
                asyncio.run(cli_scan(
                    target=args.cli,
                    depth=args.depth,
                    output_file=args.output,
                    export_format=args.format,
                ))
            else:
                asyncio.run(cli_interactive())
        else:
            # Default to web dashboard
            run_web(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\n[!] AETHER terminated by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
