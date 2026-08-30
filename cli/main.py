"""
AETHER CLI — Autonomous Cyber-Intelligence Command Line Interface
Provides full headless, scriptable, and interactive terminal investigation capabilities.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

from aether.config.settings import settings
from aether.orchestration.engine import OrchestrationEngine
import aether.perception.tools
from aether.perception.tools.registry import registry
from aether.core.logger import logger


# ── ANSI Terminal Styling ───────────────────────────────────────────────────

class Colors:
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


BANNER = f"""{Colors.CYAN}{Colors.BOLD}
    █████╗ ███████╗████████╗██╗  ██╗███████╗██████╗ 
   ██╔══██╗██╔════╝╚══██╔══╝██║  ██║██╔════╝██╔══██╗
   ███████║█████╗     ██║   ███████║█████╗  ██████╔╝
   ██╔══██║██╔══╝     ██║   ██╔══██║██╔══╝  ██╔══██╗
   ██║  ██║███████╗   ██║   ██║  ██║███████╗██║  ██║
   ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝{Colors.RESET}
{Colors.DIM}   Autonomous Cyber-Intelligence & Neural OSINT Engine v3.0{Colors.RESET}
"""


def print_banner():
    print(BANNER)


def print_status(message: str, level: str = "info"):
    tag_map = {
        "info": f"{Colors.BLUE}[*]{Colors.RESET}",
        "success": f"{Colors.GREEN}[+]{Colors.RESET}",
        "warn": f"{Colors.YELLOW}[!]{Colors.RESET}",
        "error": f"{Colors.RED}[-]{Colors.RESET}",
        "step": f"{Colors.MAGENTA}[⚡]{Colors.RESET}",
    }
    tag = tag_map.get(level, f"{Colors.BLUE}[*]{Colors.RESET}")
    print(f" {tag} {message}")


# ── CLI Subcommands ─────────────────────────────────────────────────────────

async def cli_scan(
    target: str,
    depth: Optional[int] = None,
    output_file: Optional[str] = None,
    export_format: str = "md",
    verbose: bool = False,
):
    """Executes a full autonomous intelligence investigation from the terminal."""
    print_banner()
    print_status(f"Initializing AETHER Investigation on Target: {Colors.BOLD}{target}{Colors.RESET}", "info")
    
    if depth:
        settings.MAX_SEARCH_DEPTH = depth
    
    print_status(f"Engine Provider: {Colors.CYAN}{settings.LLM_PROVIDER.upper()}{Colors.RESET} | Max Depth: {settings.MAX_SEARCH_DEPTH} steps", "info")
    print_status(f"Active Models: Planner={settings.MODEL_FAST.split('/')[-1]} | Critic={settings.MODEL_CRITIC.split('/')[-1]} | Reasoner={settings.MODEL_DEEP.split('/')[-1]}", "info")
    print("-" * 75)

    engine = OrchestrationEngine(target_seed=target)
    t_start = time.time()

    try:
        await engine.run_investigation()
    except KeyboardInterrupt:
        print_status("\nInvestigation paused by user. Synthesizing discovered evidence...", "warn")

    duration = round(time.time() - t_start, 2)
    entities = engine.state.discovered_entities
    tasks = engine.state.completed_tasks

    print("-" * 75)
    print_status(f"Investigation Finished in {duration}s", "success")
    print_status(f"Discovered Entities: {Colors.BOLD}{len(entities)}{Colors.RESET} | Tasks Executed: {Colors.BOLD}{len(tasks)}{Colors.RESET}", "success")
    
    # Entity summary table
    if entities:
        print(f"\n{Colors.BOLD}Discovered Entity Matrix:{Colors.RESET}")
        for e in entities[:20]:
            print(f"  • {Colors.CYAN}[{e.type.value.upper()}]{Colors.RESET} {Colors.BOLD}{e.id}{Colors.RESET}")
        if len(entities) > 20:
            print(f"  {Colors.DIM}... and {len(entities) - 20} more entities.{Colors.RESET}")

    # Output Export
    if output_file:
        out_path = Path(output_file).resolve()
        if export_format == "json":
            data = {
                "target": target,
                "duration_seconds": duration,
                "entities": [e.model_dump() for e in entities],
                "tasks": [t.model_dump() for t in tasks],
                "dossier": engine.dossier,
            }
            out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        else:
            out_path.write_text(engine.dossier or "No dossier synthesized.", encoding="utf-8")
        print_status(f"Report exported to: {Colors.BOLD}{out_path}{Colors.RESET}", "success")
    else:
        # Print Dossier directly
        if engine.dossier:
            print("\n" + "=" * 75)
            print(f"{Colors.BOLD}EXECUTIVE INTELLIGENCE DOSSIER{Colors.RESET}")
            print("=" * 75)
            print(engine.dossier)
            print("=" * 75)


async def cli_run_tool(tool_name: str, params_json: str):
    """Executes a single tool live from the terminal."""
    tool = registry.get_tool(tool_name)
    if not tool:
        print_status(f"Tool '{tool_name}' not found in registered Arsenal.", "error")
        print_status(f"Run 'python run.py --list-tools' to see available tools.", "info")
        sys.exit(1)

    try:
        params = json.loads(params_json) if params_json else {}
    except Exception as e:
        print_status(f"Invalid JSON parameters: {e}", "error")
        sys.exit(1)

    print_status(f"Executing Arsenal Tool: {Colors.BOLD}{tool_name}{Colors.RESET}...", "step")
    t0 = time.time()
    res = await tool.execute(**params)
    dt = round((time.time() - t0) * 1000, 2)

    print("-" * 75)
    if res.success:
        print_status(f"Tool Execution Succeeded in {dt}ms", "success")
        print(json.dumps(res.data, indent=2))
    else:
        print_status(f"Tool Execution Failed in {dt}ms: {res.error}", "error")


def cli_list_tools():
    """Prints a formatted catalog of all 34 registered Arsenal tools."""
    print_banner()
    tools = registry.list_tools()
    print(f"{Colors.BOLD}AETHER OSINT & Reconnaissance Arsenal ({len(tools)} Tools Registered):{Colors.RESET}\n")

    for i, t in enumerate(tools, 1):
        name = t.get("name", "")
        desc = t.get("description", "")
        caps = ", ".join(t.get("capabilities", []))
        print(f"  {Colors.CYAN}{i:02d}. {Colors.BOLD}{name:<28}{Colors.RESET} {desc}")
        if caps:
            print(f"      {Colors.DIM}Caps: {caps}{Colors.RESET}")
    print()


def cli_show_config():
    """Displays active configuration and model provider parameters."""
    print_banner()
    print(f"{Colors.BOLD}AETHER System Configuration & Model Mapping:{Colors.RESET}\n")
    print(f"  • {Colors.CYAN}LLM Provider:{Colors.RESET}          {settings.LLM_PROVIDER.upper()}")
    if settings.LLM_PROVIDER == "openai_compatible":
        print(f"  • {Colors.CYAN}Custom API URL:{Colors.RESET}        {settings.CUSTOM_API_BASE_URL}")
        print(f"  • {Colors.CYAN}API Key Configured:{Colors.RESET}    {'Yes (Hidden)' if settings.CUSTOM_API_KEY else 'No'}")
    else:
        print(f"  • {Colors.CYAN}Ollama Base URL:{Colors.RESET}       {settings.OLLAMA_BASE_URL}")

    print(f"\n{Colors.BOLD}Neural Role Mapping:{Colors.RESET}")
    print(f"  • Fast Planner:              {settings.MODEL_FAST}")
    print(f"  • Aggressive Tool Caller:    {settings.MODEL_AGGRESSIVE_FAST}")
    print(f"  • Red-Team Critic:           {settings.MODEL_CRITIC}")
    print(f"  • Vision VLM Model:          {settings.MODEL_VLM}")
    print(f"  • Deep Reasoner / Dossier:   {settings.MODEL_DEEP}")
    print(f"  • Heavy Reasoning Fallback:  {settings.MODEL_DEEP_FALLBACK}")

    print(f"\n{Colors.BOLD}Cognitive Budgets:{Colors.RESET}")
    print(f"  • Max Search Depth:          {settings.MAX_SEARCH_DEPTH}")
    print(f"  • Hypothesis Limit:          {settings.HYPOTHESIS_RECURSION_LIMIT}")
    print(f"  • Confidence Threshold:      {settings.ENTITY_CONFIDENCE_THRESHOLD}")
    print()


async def cli_interactive():
    """Runs interactive terminal shell for continuous OSINT scouting."""
    print_banner()
    print(f"{Colors.BOLD}AETHER Interactive Shell{Colors.RESET}")
    print(f"Type a target (domain, IP, username, email, phone) to start investigation.")
    print(f"Commands: {Colors.CYAN}:tools{Colors.RESET} | {Colors.CYAN}:config{Colors.RESET} | {Colors.CYAN}:exit{Colors.RESET}\n")

    while True:
        try:
            target = input(f"{Colors.BOLD}{Colors.GREEN}aether> {Colors.RESET}").strip()
            if not target:
                continue
            if target.lower() in (":exit", "exit", "quit", ":q"):
                print_status("Exiting AETHER interactive shell. Goodbye.", "info")
                break
            elif target.lower() in (":tools", "tools"):
                cli_list_tools()
            elif target.lower() in (":config", "config"):
                cli_show_config()
            else:
                await cli_scan(target=target)
        except (KeyboardInterrupt, EOFError):
            print("\n")
            break
