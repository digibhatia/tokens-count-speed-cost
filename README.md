# Compare Claude models: tokens, time and cost

Runs 5 prompts on Opus, Sonnet and Haiku one by one and prints tokens, time, speed and cost, plus a summary table.
One file to read: `simple_model_compare.py`.

## Steps (VS Code terminal)

1. Open this folder in VS Code (`File -> Open Folder`), then `Terminal -> New Terminal`.
2. Create and activate a virtual environment:
   - Windows PowerShell: `python -m venv .venv` then `.\.venv\Scripts\Activate.ps1`
   - macOS / Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
3. Install packages: `pip install -r requirements.txt`
4. Create your key file: copy `.env.example` to `.env` (Windows: `Copy-Item .env.example .env`; macOS/Linux: `cp .env.example .env`),
   open `.env` and replace `sk-ant-your-key-here` with your key. No quotes or spaces.
5. Run: `python simple_model_compare.py`

Options: `--prompt 2` (one prompt), `--models haiku,sonnet` (pick models), `--list` (show prompts).

## Things to try
- Edit the `PROMPTS` list at the top and add your own question (synthetic text only, no real data).
- Which model got the calculation in prompt 2 right (answer: 620)? Which stayed within about 80 words in prompt 3?
- Which model handled the trap in prompt 5 honestly?
- Is the most expensive model worth it for each prompt?

## Notes
- Prices in the file are per million tokens as published in October 2026 and change over time; check
  https://platform.claude.com/docs/en/about-claude/pricing and edit `PRICES`.
- Model IDs are at the top of the file; change them if your organisation approved different ones.
- Answers vary between runs. Never commit `.env`.

## Troubleshooting
- `ANTHROPIC_API_KEY is missing`: `.env` is not in this folder, or still has the sample value.
- `ModuleNotFoundError`: the virtual environment is not active, or step 3 was skipped.
- `404 / model not found`: edit the model IDs in `MODELS`.
- `401`: wrong key. `429`: wait a few seconds and run again.
