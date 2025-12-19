import os
import json
from google import genai

MODEL = "gemini-2.5-flash"

PROMPT = """
You are a Senior QA Lead and Requirements Analyst.

Evaluate the requirement and return ONLY valid JSON in this exact schema:

{
  "summary": "string",
  "clarity_score": 0,
  "clarity_score_reason": "string",.venv/bin/activate
  "ambiguities": ["string"],
  "missing_information": ["string"],
  "assumptions": ["string"],
  "risks_and_dependencies": ["string"],
  "edge_cases": ["string"],
  "acceptance_criteria": ["string"],
  "test_scenarios": ["string"]
}

Rules:
- clarity_score must be an integer from 0 to 100.
- Keep each bullet short and specific.

Requirement:
{{REQUIREMENT}}
""".strip()


def read_requirement() -> str:
    print("Paste your requirement. Press Enter on an empty line to finish:\n")
    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def extract_json(text: str) -> dict:
    # If model adds extra text, extract the first JSON block
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON found in output:\n" + text)
    return json.loads(text[start:end + 1])


def main():
    requirement = read_requirement()
    if not requirement:
        print("No requirement provided. Exiting.")
        return

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])  # reads GEMINI_API_KEY from environment
    prompt = PROMPT.replace("{{REQUIREMENT}}", requirement)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    raw_text = (response.text or "").strip()
    report = extract_json(raw_text)

    print("\n============================")
    print(" Requirement Review Report")
    print("============================\n")

    print(f"Summary: {report.get('summary')}\n")
    print(f"Clarity Score: {report.get('clarity_score')} / 100")
    print(f"Reason: {report.get('clarity_score_reason')}\n")

    def show_list(title, items):
        print(title)
        if not items:
            print("- (none)\n")
            return
        for item in items:
            print(f"- {item}")
        print()

    show_list("Ambiguities:", report.get("ambiguities", []))
    show_list("Missing information:", report.get("missing_information", []))
    show_list("Assumptions:", report.get("assumptions", []))
    show_list("Risks & dependencies:", report.get("risks_and_dependencies", []))
    show_list("Edge cases:", report.get("edge_cases", []))
    show_list("Acceptance criteria:", report.get("acceptance_criteria", []))
    show_list("Suggested test scenarios:", report.get("test_scenarios", []))

    # Save output to a file
    with open("last_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("✅ Saved JSON output to last_report.json")


if __name__ == "__main__":
    main()