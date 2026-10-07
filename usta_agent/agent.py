"""The Gemini-powered agent: an LLM that decides when/how to call our tools."""

from __future__ import annotations

import os

from google import genai
from google.genai import types

from usta_agent.tools import AGENT_TOOLS

DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """\
You are a helpful junior tennis tournament scout for a family in ZIP code 30022
(Alpharetta / Johns Creek, Georgia).

Default search criteria (use unless the user asks otherwise):
- Division: Boys 12 & Under (12U) Singles
- USTA junior levels: Level 4 and Level 5
- Within 200 miles of ZIP 30022
- Next 6 months, listed by date and then by proximity

Rules:
- ALWAYS call the `search_tournaments` tool to get real data. Never invent tournaments.
- The tool already prints a full table and saves a CSV, so do not repeat every row.
  Instead give a short summary: number found, the 3-5 best options (soonest/closest),
  any weekends with multiple choices, and the CSV path.
- If the tool returns an error, explain it plainly and suggest a fix
  (e.g. run with --sample to use offline data).
- Remind the user to confirm entry deadlines and draw details on playtennis.usta.com.
"""

DEFAULT_GOAL = (
    "Find USTA Boys 12U Singles tournaments at Level 4 or Level 5 near ZIP 30022, "
    "listed by date and proximity, and summarize the best options."
)


class TournamentAgent:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file or use --no-llm.")
        self.client = genai.Client(api_key=api_key)
        self.chat = self.client.chats.create(
            model=model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=AGENT_TOOLS,  # SDK handles automatic function calling.
                temperature=0.2,
            ),
        )

    def ask(self, message: str) -> str:
        response = self.chat.send_message(message)
        return response.text or "(no response)"
