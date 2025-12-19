# streamlit_app.py
import json
import os
import re
from typing import Any, Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv
from google import genai

# ----------------------------
# Config
# ----------------------------
load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")  # you can change later
API_KEY = os.getenv("GEMINI_API_KEY")


# ----------------------------
# Helpers
# ----------------------------
def get_client() -> genai.Client:
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY not found. Add it to .env file.")
    return genai.Client(api_key=API_KEY)


def extract_json(text: str) -> Dict[str, Any]:
    """
    Tries to parse JSON from model output robustly:
    - If output is pure JSON, parse directly
    - Else find the first {...} JSON block and parse it
    """
    text = text.strip()

    # 1) direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) find a JSON object block
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("Model did not return JSON. Raw output:\n" + text)

    json_str = match.group(0)
    try:
        return json.loads(json_str)
    except Exception as e:
        raise ValueError(f"Failed to parse JSON block: {e}\n\nJSON block:\n{json_str}\n\nRaw:\n{text}")


def call_llm(prompt: str) -> Dict[str, Any]:
    client = get_client()
    resp = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )
    # google-genai returns text on resp.text
    return extract_json(resp.text)


# ----------------------------
# Prompt Builders (IMPORTANT)
# Use .format() so we don't fight f-string { } escaping
# ----------------------------
ANALYZE_PROMPT = """
You are a Senior QA Lead and Requirements Analyst.

Task:
Analyze the requirement and return a structured quality report.

Return ONLY valid JSON in this exact schema (no markdown, no extra text):
{schema}

Rules:
- clarity_score must be an integer 0–100.
- Keep each list item short and specific (one sentence).
- Acceptance criteria should be atomic and testable. Prefer Gherkin.
- Test scenarios: provide 6–12 realistic scenarios. Each item should be a single line:
  "Title — Preconditions — Steps — Expected Result" (short but concrete).
- Be specific about missing info, assumptions, edge cases, integrations, error handling, security, and performance.

Requirement:
{requirement}
""".strip()

CLARIFY_PROMPT = """
You are a Senior QA Lead.

Task:
Ask clarifying questions to remove ambiguity and make the requirement testable.

Return ONLY valid JSON in this exact schema (no markdown, no extra text):
{schema}

Rules:
- Ask 6–10 focused, answerable questions.
- Prefer questions that produce concrete values or boolean choices (limits, formats, expiry, retries, roles, permissions).
- Order by importance (most impactful to least).
- why_it_matters must be one concise sentence.

Requirement:
{requirement}
""".strip()

IMPROVE_PROMPT = """
You are a Senior QA Lead and Requirements Analyst.

Task:
Use the stakeholder answers to improve the requirement analysis and produce a refreshed quality report.

Return ONLY valid JSON in this exact schema (no markdown, no extra text):
{schema}

Rules:
- clarity_score must be an integer 0–100.
- Keep each list item short and specific (one sentence).
- Acceptance criteria: atomic, testable, prefer Gherkin.
- Test scenarios: provide 6–12 realistic scenarios:
  "Title — Preconditions — Steps — Expected Result".
- If any answers are still vague, call that out under missing_information.

Original Requirement:
{requirement}

Clarifying Q&A:
{qa_text}
""".strip()


ANALYZE_SCHEMA = {
    "summary": "string",
    "clarity_score": 0,
    "clarity_score_reason": "string",
    "ambiguities": ["string"],
    "missing_information": ["string"],
    "assumptions": ["string"],
    "risks_and_dependencies": ["string"],
    "edge_cases": ["string"],
    "acceptance_criteria": ["string"],
    "test_scenarios": ["string"],
}

CLARIFY_SCHEMA = {
    "clarifying_questions": [
        {"id": "Q1", "question": "string", "why_it_matters": "string"}
    ]
}


# ----------------------------
# Core Functions
# ----------------------------
def analyze_requirement(requirement: str) -> Dict[str, Any]:
    prompt = ANALYZE_PROMPT.format(schema=json.dumps(ANALYZE_SCHEMA, indent=2), requirement=requirement)
    return call_llm(prompt)


def generate_clarifying_questions(requirement: str) -> Dict[str, Any]:
    prompt = CLARIFY_PROMPT.format(schema=json.dumps(CLARIFY_SCHEMA, indent=2), requirement=requirement)
    return call_llm(prompt)


def improve_with_answers(requirement: str, q_and_a: List[Dict[str, str]]) -> Dict[str, Any]:
    qa_lines = []
    for item in q_and_a:
        qa_lines.append(f"{item['id']}. {item['question']}\nAnswer: {item.get('answer','').strip()}")
    qa_text = "\n\n".join(qa_lines).strip()

    prompt = IMPROVE_PROMPT.format(
        schema=json.dumps(ANALYZE_SCHEMA, indent=2),
        requirement=requirement,
        qa_text=qa_text
    )
    return call_llm(prompt)


def render_report(report: Dict[str, Any]) -> None:
    st.subheader("Summary")
    st.write(report.get("summary", ""))

    score = report.get("clarity_score", 0)
    st.subheader("Clarity Score")
    st.metric("Score (0–100)", int(score) if isinstance(score, (int, float, str)) else 0)
    st.caption(report.get("clarity_score_reason", ""))

    def render_list(title: str, items: Optional[List[str]]):
        st.subheader(title)
        if not items:
            st.write("—")
            return
        for x in items:
            st.write(f"- {x}")

    render_list("Ambiguities", report.get("ambiguities"))
    render_list("Missing Information", report.get("missing_information"))
    render_list("Assumptions", report.get("assumptions"))
    render_list("Risks & Dependencies", report.get("risks_and_dependencies"))
    render_list("Edge Cases", report.get("edge_cases"))
    render_list("Acceptance Criteria", report.get("acceptance_criteria"))
    render_list("Test Scenarios", report.get("test_scenarios"))

    st.divider()
    st.download_button(
        "Download JSON report",
        data=json.dumps(report, indent=2),
        file_name="report.json",
        mime="application/json"
    )


# ----------------------------
# UI
# ----------------------------
st.set_page_config(page_title="AI Requirement Quality Analyzer (Gemini)", layout="wide")

st.title("AI Requirement Quality Analyzer (Gemini)")
st.caption("Paste a requirement/user story and get a quality review + score.")

tab1, tab2 = st.tabs(["Analyzer", "Agent Mode (Clarify → Improve)"])

with tab1:
    requirement = st.text_area("Requirement", height=200, placeholder="Example: User should be able to reset password using OTP.")
    if st.button("Analyze", type="primary"):
        if not API_KEY:
            st.error("GEMINI_API_KEY not found. Add it to .env file (same folder as this project).")
        elif not requirement.strip():
            st.warning("Please paste a requirement first.")
        else:
            with st.spinner("Analyzing requirement..."):
                try:
                    report = analyze_requirement(requirement.strip())
                    st.session_state["last_report"] = report
                    st.success("Analysis complete.")
                    render_report(report)
                except Exception as e:
                    st.error(str(e))

with tab2:
    st.write("Step 1: Generate clarifying questions. Step 2: Answer them. Step 3: Improve analysis using answers.")

    agent_req = st.text_area("Requirement (Agent Mode)", height=180, key="agent_requirement")

    colA, colB = st.columns(2)
    with colA:
        if st.button("1) Generate clarifying questions"):
            if not API_KEY:
                st.error("GEMINI_API_KEY not found. Add it to .env file.")
            elif not agent_req.strip():
                st.warning("Please paste a requirement first.")
            else:
                with st.spinner("Generating clarifying questions..."):
                    try:
                        q_report = generate_clarifying_questions(agent_req.strip())
                        questions = q_report.get("clarifying_questions", [])
                        st.session_state["agent_questions"] = questions
                        st.session_state["agent_req"] = agent_req.strip()
                        st.success("Questions generated.")
                    except Exception as e:
                        st.error(str(e))

    with colB:
        if st.button("Reset Agent State"):
            for k in ["agent_questions", "agent_req", "agent_answers", "improved_report"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.success("Reset done.")

    questions = st.session_state.get("agent_questions", [])
    if questions:
        st.subheader("Answer the clarifying questions")
        answers: List[Dict[str, str]] = []
        for q in questions:
            qid = q.get("id", "")
            qtext = q.get("question", "")
            why = q.get("why_it_matters", "")
            st.markdown(f"**{qid}: {qtext}**")
            st.caption(why)
            ans = st.text_input(f"Answer for {qid}", key=f"ans_{qid}")
            answers.append({"id": qid, "question": qtext, "answer": ans})

        if st.button("2) Improve analysis using my answers", type="primary"):
            req = st.session_state.get("agent_req", "").strip()
            if not req:
                st.error("Missing requirement in session. Click Reset and try again.")
            else:
                with st.spinner("Improving analysis..."):
                    try:
                        improved = improve_with_answers(req, answers)
                        st.session_state["improved_report"] = improved
                        st.success("Improved report generated.")
                        render_report(improved)
                    except Exception as e:
                        st.error(str(e))
    else:
        st.info("Click **1) Generate clarifying questions** to begin.")

# Footer debug (optional)
with st.expander("Debug (optional)"):
    st.write("MODEL:", MODEL)
    st.write("API key loaded:", "Yes" if API_KEY else "No")