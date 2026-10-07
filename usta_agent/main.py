"""USTA Tournament Agent - finds Boys 12U Singles L4/L5 tournaments near a ZIP code.

Usage:
    python main.py                 # agent run with default goal (needs GEMINI_API_KEY)
    python main.py --chat          # interactive chat with the agent
    python main.py --no-llm        # skip the LLM, just print table + CSV
    python main.py --sample        # use offline sample data (no USTA request)
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from usta_agent import tools


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Find USTA Boys 12U Singles tournaments near you.")
    p.add_argument("--zip", default="30022", help="ZIP code to search from (default: 30022)")
    p.add_argument("--radius", type=int, default=200, help="Search radius in miles (default: 200)")
    p.add_argument("--months", type=int, default=6, help="Months ahead to search (default: 6)")
    p.add_argument("--levels", default="4,5", help="Comma-separated levels (default: 4,5)")
    p.add_argument("--sort", choices=["date", "distance"], default="date", help="Sort order (default: date)")
    p.add_argument("--csv", default="results/tournaments_12u_boys.csv", help="CSV output path")
    p.add_argument("--sample", action="store_true", help="Use offline sample data instead of live USTA data")
    p.add_argument("--no-llm", action="store_true", help="Run the search without the Gemini agent")
    p.add_argument("--chat", action="store_true", help="Interactive chat mode")
    return p.parse_args(argv)


def run_without_llm(args: argparse.Namespace) -> None:
    levels = [int(x) for x in args.levels.split(",") if x.strip()]
    tools.run_search(args.zip, args.radius, args.months, levels, args.sort)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv)
    tools.SETTINGS["use_sample"] = args.sample
    tools.SETTINGS["csv_path"] = args.csv

    has_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if args.no_llm or not has_key:
        if not args.no_llm:
            print("GEMINI_API_KEY not found; running without the LLM (see README).")
        run_without_llm(args)
        return 0

    from usta_agent.agent import TournamentAgent  # imported lazily so --no-llm needs no SDK

    agent = TournamentAgent()
    goal = (
        f"Find USTA Boys 12U Singles tournaments, levels {args.levels}, within {args.radius} miles "
        f"of ZIP {args.zip}, over the next {args.months} months, sorted by {args.sort}. "
        "Summarize the best options."
    )

    if not args.chat:
        print(agent.ask(goal))
        return 0

    print("USTA Tournament Agent - type 'quit' to exit.")
    print("Try: 'find tournaments', 'only Level 4 within 100 miles', 'sort by distance'.\n")
    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user.lower() in {"quit", "exit", "q"}:
            break
        if user:
            print(f"\nAgent: {agent.ask(user)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
