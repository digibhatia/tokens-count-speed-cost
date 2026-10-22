"""
simple_model_compare.py  -  run the same prompts on different Claude models, one by one
=========================================================================================
A single, self-contained file. Read it top to bottom - it is only about 150 lines of logic.

What it does
------------
For each prompt below, it calls each model in turn (Opus, then Sonnet, then Haiku),
prints the answer, and shows the numbers that matter in real projects:

    input tokens | output tokens | time | tokens per second | cost in US dollars

At the end you get one summary table so you can compare the models side by side.

Before you run
--------------
1. Put your key in the .env file next to this file (copy .env.example to .env):
       ANTHROPIC_API_KEY=sk-ant-...your key...
2. Activate the virtual environment and install packages once:  pip install -r requirements.txt
3. Run in the VS Code terminal, from this folder:

       python simple_model_compare.py
       python simple_model_compare.py --prompt 2
       python simple_model_compare.py --models haiku,sonnet
       python simple_model_compare.py --list

Try it yourself: edit PROMPTS below (add your own, using synthetic text only), save, run again.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv   # reads KEY=value lines from the .env file
import anthropic                 # the official Anthropic Python SDK

# ---------------------------------------------------------------------------------------
# 1. Load the API key from .env
# ---------------------------------------------------------------------------------------
# The .env file lives in the same folder as this file. Using an explicit
# path means the key is found no matter which folder you run the script from.
REPO_ROOT = Path(__file__).resolve().parent
load_dotenv(REPO_ROOT / ".env")

# ---------------------------------------------------------------------------------------
# 2. The models to compare (edit if your organisation approved different ones)
# ---------------------------------------------------------------------------------------
# short name -> model ID sent to the API
MODELS = {
    "opus":   "claude-opus-5-5",     # strongest, slowest, most expensive
    "sonnet": "claude-sonnet-5-5",   # balanced
    "haiku":  "claude-haiku-5-5",    # fastest, cheapest
}

# Price in US dollars per MILLION tokens: (input, output).
# Taken from Anthropic's public pricing page in October 2026 (Haiku: price for prompts up to 100K tokens).
# PRICES CHANGE - check https://platform.claude.com/docs/en/about-claude/pricing and edit here.
PRICES = {
    "opus":   (4.00, 20.00),
    "sonnet": (2.00, 10.00),
    "haiku":  (0.10, 0.50),
}

# ---------------------------------------------------------------------------------------
# 3. The prompts (add your own!)
# ---------------------------------------------------------------------------------------
PROMPTS = [
    # 1 - explain simply: do the models differ in clarity and length?
    "Explain in 3 sentences what an LLM context window is, for a non-technical manager.",

    # 2 - reasoning + arithmetic. Correct answer: 99.5 - 98.6 = 0.9 -> ONE full 0.5-point step -> 5% of 12,400 = 620.
    "A vendor charges 12,400 per month. If availability falls below 99.5%, the customer gets a credit of "
    "5% of the monthly fee for each FULL 0.5 percentage points below 99.5%, up to a maximum of 20%. "
    "Availability was 98.6%. How much is the credit? Show your steps briefly.",

    # 3 - writing: tone and instruction-following (the word limit is a test!).
    "Write a polite email of about 80 words declining a refund request because the 30-day return window has passed.",

    # 4 - code
    "Write a Python function that returns the n-th Fibonacci number without recursion. Include a one-line docstring.",

    # 5 - honesty trap: nobody can know this. A good model says so instead of inventing a number.
    "What was the exact population of the city of Lucknow in the 2031 census?",
]

MAX_TOKENS = 600   # upper limit on the answer length: keeps cost and waiting time small


# ---------------------------------------------------------------------------------------
# 4. Helper functions
# ---------------------------------------------------------------------------------------
def cost_usd(tier: str, input_tokens: int, output_tokens: int) -> float:
    """Dollars = (tokens / 1,000,000) x price per million - separately for input and output."""
    price_in, price_out = PRICES[tier]
    return input_tokens / 1_000_000 * price_in + output_tokens / 1_000_000 * price_out


def ask(client: anthropic.Anthropic, tier: str, prompt: str) -> dict:
    """Send ONE prompt to ONE model and return the answer plus all the metrics."""
    started = time.perf_counter()                       # start the stopwatch
    response = client.messages.create(
        model=MODELS[tier],
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],  # a conversation is a list of messages
    )
    seconds = time.perf_counter() - started             # stop the stopwatch

    # The reply is a list of content blocks; join the text ones.
    answer = "".join(block.text for block in response.content if block.type == "text").strip()
    in_tok, out_tok = response.usage.input_tokens, response.usage.output_tokens   # billing numbers come from the API
    return {
        "tier": tier,
        "model": response.model,         # the model that really answered
        "answer": answer,
        "in_tok": in_tok,
        "out_tok": out_tok,
        "seconds": seconds,
        "tok_per_s": out_tok / seconds if seconds > 0 else 0.0,
        "cost": cost_usd(tier, in_tok, out_tok),
        "cut_off": response.stop_reason == "max_tokens",   # True if the answer hit our length limit
    }


def show(result: dict) -> None:
    """Print one model's answer and its metrics."""
    print(f"\n--- {result['tier'].upper()}  ({result['model']}) " + "-" * 30)
    print(result["answer"])
    if result["cut_off"]:
        print(f"[answer was cut off at {MAX_TOKENS} tokens]")
    print(f"\n  tokens in/out: {result['in_tok']}/{result['out_tok']}   "
          f"time: {result['seconds']:.1f}s   speed: {result['tok_per_s']:.0f} tok/s   "
          f"cost: ${result['cost']:.5f}")


def summary(all_results: list[dict]) -> None:
    """Add up the numbers per model across all prompts and print a comparison table."""
    totals: dict[str, dict] = {}
    for r in all_results:
        t = totals.setdefault(r["tier"], {"in": 0, "out": 0, "sec": 0.0, "cost": 0.0, "n": 0})
        t["in"] += r["in_tok"]; t["out"] += r["out_tok"]; t["sec"] += r["seconds"]; t["cost"] += r["cost"]; t["n"] += 1

    cheapest = min(t["cost"] for t in totals.values()) or 1e-9   # to show "x times more expensive"
    print("\n" + "=" * 78)
    print("SUMMARY (all prompts)")
    print(f"{'model':<8}{'prompts':>8}{'tokens in':>11}{'tokens out':>12}{'total sec':>11}{'cost $':>11}{'vs cheapest':>13}")
    print("-" * 78)
    for tier, t in totals.items():
        print(f"{tier:<8}{t['n']:>8}{t['in']:>11}{t['out']:>12}{t['sec']:>11.1f}{t['cost']:>11.5f}{t['cost'] / cheapest:>12.1f}x")
    print("=" * 78)
    print("Questions: Did the pricier model give a better answer on every prompt? On which prompt was the")
    print("cheap model good enough? Which model handled prompt 5 (the trap) most honestly?")


# ---------------------------------------------------------------------------------------
# 5. Main program
# ---------------------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Run prompts on several Claude models and compare metrics")
    parser.add_argument("--prompt", type=int, help="run only this prompt number (1-%d)" % len(PROMPTS))
    parser.add_argument("--models", default=",".join(MODELS), help="comma-separated, default: all (opus,sonnet,haiku)")
    parser.add_argument("--list", action="store_true", help="show the prompts and exit")
    args = parser.parse_args()

    if args.list:
        for i, p in enumerate(PROMPTS, 1):
            print(f"{i}. {p}\n")
        return

    # Check the key before doing anything else, with a friendly message instead of a stack trace.
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip().strip('"').strip("'")
    if not key or key.lower().startswith("sk-ant-your"):
        sys.exit(f"ANTHROPIC_API_KEY is missing or still the sample value.\nEdit {REPO_ROOT / '.env'} and run again.")

    tiers = [t.strip() for t in args.models.split(",") if t.strip()]
    for t in tiers:
        if t not in MODELS:
            sys.exit(f"Unknown model '{t}'. Choose from: {', '.join(MODELS)}")

    if args.prompt:
        if not 1 <= args.prompt <= len(PROMPTS):
            sys.exit(f"--prompt must be between 1 and {len(PROMPTS)}")
        numbered = [(args.prompt, PROMPTS[args.prompt - 1])]
    else:
        numbered = list(enumerate(PROMPTS, 1))

    client = anthropic.Anthropic(api_key=key)     # the connection to the API (retries transient errors by itself)
    all_results: list[dict] = []

    for number, prompt in numbered:
        print("\n" + "#" * 78)
        print(f"PROMPT {number}: {prompt}")
        print("#" * 78)
        for tier in tiers:                          # one model after another
            try:
                result = ask(client, tier, prompt)
            except anthropic.APIError as exc:       # wrong key, unknown model ID, rate limit, network ...
                print(f"\n--- {tier.upper()} FAILED: {type(exc).__name__}: {exc}")
                continue
            show(result)
            all_results.append(result)

    if all_results:
        summary(all_results)


if __name__ == "__main__":
    main()
