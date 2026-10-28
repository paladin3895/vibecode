#!/usr/bin/env python3
"""Run a Browser Use agent against a Chromium already started with
--remote-debugging-port (see launch_chromium.sh).

Usage:
    python run_agent.py "Go to example.com and report the page title"
    python run_agent.py --cdp-url http://127.0.0.1:9222 --max-steps 20 "<task>"

LLM selection (first key found in env / .env wins, unless --llm is given):
    BROWSER_USE_API_KEY -> ChatBrowserUse
    OPENAI_API_KEY      -> ChatOpenAI
    ANTHROPIC_API_KEY   -> ChatAnthropic
    GOOGLE_API_KEY      -> ChatGoogle
"""
import argparse
import asyncio
import os
import sys
import urllib.request

try:
    from dotenv import load_dotenv
    from browser_use import Agent, Browser
except ImportError as exc:
    sys.exit(
        f"Missing dependency ({exc.name}). Install into the configured env: "
        "pip install browser-use"
    )

LLM_BY_ENV = [
    ("BROWSER_USE_API_KEY", "browser-use", "ChatBrowserUse"),
    ("OPENAI_API_KEY", "openai", "ChatOpenAI"),
    ("ANTHROPIC_API_KEY", "anthropic", "ChatAnthropic"),
    ("GOOGLE_API_KEY", "google", "ChatGoogle"),
]


# Vision-capable defaults; ChatBrowserUse needs no model name.
DEFAULT_MODEL = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-0",
    "google": "gemini-2.5-flash",
}


def build_llm(name: str | None, model: str | None):
    import browser_use

    for env_key, key_name, cls_name in LLM_BY_ENV:
        if (name and name == key_name) or (not name and os.getenv(env_key)):
            if not os.getenv(env_key):
                sys.exit(f"{env_key} is not set (put it in .env or the environment).")
            cls = getattr(browser_use, cls_name)
            if key_name == "browser-use":
                return cls()
            return cls(model=model or DEFAULT_MODEL[key_name])
    sys.exit(
        "No LLM API key found. Set one of: "
        + ", ".join(k for k, _, _ in LLM_BY_ENV)
    )


def check_cdp(cdp_url: str) -> None:
    try:
        with urllib.request.urlopen(f"{cdp_url.rstrip('/')}/json/version", timeout=3):
            pass
    except OSError:
        sys.exit(
            f"No browser answering at {cdp_url}. Start one with "
            "scripts/launch_chromium.sh first."
        )


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("task", help="Natural-language task for the agent")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    parser.add_argument("--llm", choices=[k for _, k, _ in LLM_BY_ENV])
    parser.add_argument("--model", help="Model name (default is a vision-capable model per provider)")
    parser.add_argument("--max-steps", type=int, default=30)
    args = parser.parse_args()

    load_dotenv()
    check_cdp(args.cdp_url)

    browser = Browser(cdp_url=args.cdp_url)
    agent = Agent(task=args.task, llm=build_llm(args.llm, args.model), browser=browser)
    history = await agent.run(max_steps=args.max_steps)

    print("\n=== Final result ===")
    print(history.final_result())


if __name__ == "__main__":
    asyncio.run(main())
