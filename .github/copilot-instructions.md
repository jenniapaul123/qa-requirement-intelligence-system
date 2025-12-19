# Copilot / AI Agent Instructions — req-quality-analyzer

Purpose: Help an AI code agent become productive quickly in this small Python repo.

- **Quick start (run locally)**:
  - **Set API key**: `export GEMINI_API_KEY="YOUR_KEY"`
  - **Install dependency**: `pip install google-genai`
  - **Run**: `python req_analyzer.py` (interactive; paste requirement, then an empty line)
  - **Non-interactive**: `printf "<REQ>\n\n" | python req_analyzer.py`

- **Entry points & important files**:
  - `req_analyzer.py`: main script. Builds a prompt, calls Google GenAI (`google.genai.Client`), extracts JSON from the model output and writes `last_report.json`.
  - `last_report.json`: sample output showing the exact JSON schema the tool expects.

- **Model / API usage patterns**:
  - The script instantiates `genai.Client(api_key=os.environ['GEMINI_API_KEY'])` and calls `client.models.generate_content(...)` with `MODEL = "gemini-2.5-flash"`.
  - The prompt (`PROMPT` constant) instructs the model to return ONLY JSON in a strict schema. The agent must preserve that requirement when editing the prompt or response-handling code.

- **JSON extraction and robustness**:
  - `extract_json()` finds the first `{` and last `}` and loads that substring via `json.loads`. Keep that behavior if you need to handle extra model text — it's the intended lenient fallback.
  - Avoid changing the output file name `last_report.json` unless updating downstream references.

- **Project-specific quirks to watch**:
  - There's an accidental artifact in `PROMPT` (a stray `.venv/bin/activate` appended to the schema line). Do not remove it silently — if you change `PROMPT`, run the script to confirm the model still returns clean JSON.
  - The schema requires `clarity_score` to be an integer 0–100 and a number of specific arrays (e.g., `ambiguities`, `missing_information`). Any code that validates or transforms the model output should follow those keys exactly.

- **Editing guidance for an AI agent**:
  - When modifying `req_analyzer.py`: preserve the interactive input flow and the `extract_json()` approach unless you add robust JSON extraction tests. If you change the prompt, include an example run showing the model still returns a single JSON object.
  - If adding tests or automation, emulate interactive input with `printf` shown above or by refactoring `read_requirement()` to accept an argument for easier unit testing.

- **Examples of patterns in this repo**:
  - Prompt composition: `prompt = PROMPT.replace("{{REQUIREMENT}}", requirement)` — treat `PROMPT` as single-source-of-truth for instructions.
  - Response handling: `raw_text = (response.text or "").strip()` then `report = extract_json(raw_text)` — always guard against `None`.

- **Suggested small improvements (explicit, testable changes)**:
  - Add a small automated smoke test that runs `req_analyzer.py` with a canned requirement and asserts `last_report.json` contains required keys.
  - Add a `requirements.txt` or `pyproject.toml` listing `google-genai` and pin a minimum Python version.

- **When to ask the human owner**:
  - If you plan to change the `PROMPT` semantics (for example, expand the schema or relax the JSON-only rule), confirm desired schema changes first.
  - If you add background processes or new files that change the run workflow (Docker, CI), confirm preferred CI tooling and Python version.

Keep edits focused and testable: update `PROMPT` only with a sample run, and keep `last_report.json` schema compatibility intact.

---
Files to inspect when working here: [req_analyzer.py](req_analyzer.py#L1) and [last_report.json](last_report.json#L1).
