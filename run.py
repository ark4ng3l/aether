"""
AETHER — run.py
Unified launcher for CLI and Web modes.

Usage:
    python aether/run.py --web              Start FastAPI dashboard (default)
    python aether/run.py --cli [seed]       Run a CLI investigation
"""

import argparse
import asyncio
import sys
from pathlib import Path

# ── Path bootstrap ────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent        # aether/
PARENT_DIR = BASE_DIR.parent                      # project root
for p in (str(PARENT_DIR), str(BASE_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


def run_web():
    """Start the FastAPI dashboard with uvicorn."""
    import uvicorn
    print("Starting AETHER Web Dashboard...")
    print("  -> http://127.0.0.1:8000")
    uvicorn.run(
        "aether.api.server:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )


def run_cli(seed: str | None = None):
    """Run a single investigation in the terminal."""
    from aether.orchestration.engine import OrchestrationEngine

    if not seed:
        seed = input("Enter investigation seed (e.g. @username, domain.com): ").strip()
    if not seed:
        print("No seed provided. Exiting.")
        sys.exit(1)

    print(f"\nStarting AETHER CLI investigation for: {seed}\n")
    engine = OrchestrationEngine(target_seed=seed)
    asyncio.run(engine.run_investigation())

    if engine.dossier:
        print("\n" + "=" * 60)
        print(engine.dossier)
        print("=" * 60)
    print(f"\nInvestigation complete — {len(engine.state.discovered_entities)} entities found.")


# ------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AETHER — Autonomous Intelligence Engine",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--cli", nargs="?", const="", metavar="SEED",
                       help="Run a CLI investigation (optionally with a seed)")
    group.add_argument("--web", action="store_true", default=True,
                       help="Start the web dashboard (default)")
    args = parser.parse_args()

    try:
        if args.cli is not None:
            run_cli(args.cli or None)
        else:
            run_web()
    except KeyboardInterrupt:
        print("\nShutting down AETHER...")
        sys.exit(0)
