import os
import json
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL = "gemini-2.5-flash"

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Add it to .env file.")
    return genai.Client(api_key=api_key)

def extract_json(text: str) -> dict:
    text = (text or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON found in model output:\n{text}")
    return json.loads(text[start:end+1])

def analyze_requirement(requirement: str) -> dict:
        prompt = f"""
You are a Senior QA Lead and Requirements Analyst.

Return ONLY valid JSON in this exact schema:

{
    "summary": "string",
    "clarity_score": 0,
    "clarity_score_reason": "string",
    "ambiguities": ["string"],
    "missing_information": ["string"],
    "assumptions": ["string"],
    "risks_and_dependencies": ["string"],
    "edge_cases": ["string"],
    "acceptance_criteria": ["string"],
    "test_scenarios": ["string"]
}

Additional instructions to improve realism and testability:
- Summary: 2–3 concise sentences describing scope, primary actors, objective, and any key constraints or non-functional expectations.
- clarity_score: integer 0–100. In `clarity_score_reason` cite specific phrases from the requirement that influenced the score and why.
- acceptance_criteria: return short, atomic, testable criteria. Prefer Gherkin-style lines (Given/When/Then) if applicable, included inside each string.
- test_scenarios: produce 6–12 realistic scenarios. Each item must be a single string using this compact format:
    "Title — Type (happy/negative/edge) — Preconditions — Steps (Given/When/Then) — Expected result — Priority (P0/P1/P2)"
- For ambiguities, missing information, assumptions, risks, and edge cases: be specific and actionable (e.g., "What is the maximum password length?" or "Is email verification required?").
- When external systems or integrations are implied (APIs, payment gateways, SSO), include expected failure modes and how a tester would detect them.
- Keep list items short (one sentence) and avoid adding any keys beyond the required schema.
- Return ONLY valid JSON exactly matching the schema above.

Requirement:
{requirement}
""".strip()

    client = get_client()
    resp = client.models.generate_content(model=MODEL, contents=prompt)
    return extract_json(resp.text)

def generate_clarifying_questions(requirement: str) -> dict:
        prompt = f"""
You are a Senior QA Lead.

Goal: Ask clarifying questions to remove ambiguity and make the requirement testable.

Return ONLY valid JSON in this exact schema:

{
    "clarifying_questions": [
        {
            "id": "Q1",
            "question": "string",
            "why_it_matters": "string"
        }
    ]
}

Rules:
- Ask 6 to 10 focused, specific, and answerable questions.
- For each question, ensure `why_it_matters` explains (1) what exact information is expected in the answer, and (2) which test artifacts or acceptance criteria depend on that answer.
- Prefer questions that produce concrete values or boolean choices (e.g., limits, formats, feature flags, API endpoints, SLAs) rather than open discussion.
- Order questions by importance (most impactful to least).
- Return ONLY JSON matching the schema above.

Requirement:
{requirement}
""".strip()

    client = get_client()
    resp = client.models.generate_content(model=MODEL, contents=prompt)
    return extract_json(resp.text)

def improve_with_answers(requirement: str, q_and_a: list) -> dict:
    qa_text = "\n".join([f"{x['id']} {x['question']}\nAnswer: {x['answer']}" for x in q_and_a])

    prompt = f"""
You are a Senior QA Lead and Requirements Analyst.

You are given:
1) Original requirement
2) Clarifying Q&A from stakeholders

Return ONLY valid JSON in this exact schema:

{
    "summary": "string",
    "clarity_score": 0,
    "clarity_score_reason": "string",
    "ambiguities": ["string"],
    "missing_information": ["string"],
    "assumptions": ["string"],
    "risks_and_dependencies": ["string"],
    "edge_cases": ["string"],
    "acceptance_criteria": ["string"],
    "test_scenarios": ["string"]
}

Rules:
- Use the clarifying answers to reduce ambiguities and fill missing information. If an answer is blank or non-specific, leave it marked in `missing_information` or `ambiguities`.
- Update the summary to reflect any clarified scope or constraints (2–3 sentences).
- Update `clarity_score` and in `clarity_score_reason` cite which answers improved clarity and which issues remain.
- acceptance_criteria: where possible, convert clarified requirements into atomic, testable criteria (Gherkin-style if applicable).
- test_scenarios: produce scenarios that reference the clarified answers. For each scenario string, include mapping to acceptance criteria and an estimated test effort in minutes. Use the same compact format as before and include the estimate at the end, e.g.:
    "Title — Type — Preconditions — Steps (Given/When/Then) — Expected result — Priority — Est: 15m"
- Keep items short and actionable. Do not introduce schema changes. Return ONLY valid JSON.

Original requirement:
{requirement}

Clarifying Q&A:
{qa_text}
""".strip()

    client = get_client()
    resp = client.models.generate_content(model=MODEL, contents=prompt)
    return extract_json(resp.text)

def render_report(report: dict):
    st.subheader("Requirement Review Report")
    st.write(f"**Summary:** {report.get('summary','')}")
    st.write(f"**Clarity score:** {report.get('clarity_score','')} / 100")
    st.write(f"**Reason:** {report.get('clarity_score_reason','')}")

    def show_list(title, items):
        st.markdown(f"### {title}")
        if not items:
            st.write("(none)")
            return
        for item in items:
            st.write(f"- {item}")

    show_list("Ambiguities", report.get("ambiguities", []))
    show_list("Missing information", report.get("missing_information", []))
    show_list("Assumptions", report.get("assumptions", []))
    show_list("Risks & dependencies", report.get("risks_and_dependencies", []))
    show_list("Edge cases", report.get("edge_cases", []))
    show_list("Acceptance criteria", report.get("acceptance_criteria", []))
    show_list("Suggested test scenarios", report.get("test_scenarios", []))

    st.download_button(
        label="Download JSON report",
        data=json.dumps(report, indent=2),
        file_name="requirement_report.json",
        mime="application/json"
    )

# ---------------- UI ----------------

st.set_page_config(page_title="Requirement Quality Analyzer", layout="wide")
st.title("AI Requirement Quality Analyzer (Gemini)")

tab1, tab2 = st.tabs(["Analyzer", "Agent Mode (Clarify → Improve)"])

with tab1:
    st.write("Paste a requirement/user story and get a quality review + score.")
    requirement = st.text_area(
        "Requirement",
        height=220,
        placeholder="Example: User should be able to reset password using OTP..."
    )

    if st.button("Analyze", type="primary"):
        if not requirement.strip():
            st.warning("Please paste a requirement first.")
        else:
            with st.spinner("Analyzing with Gemini..."):
                try:
                    report = analyze_requirement(requirement.strip())
                    st.session_state["last_report"] = report
                    render_report(report)
                except Exception as e:
                    st.error(str(e))

with tab2:
    st.write("This mode behaves like a simple agent:")
    st.write("1) Generates clarifying questions → 2) You answer → 3) It re-analyzes and improves the report.")

    req2 = st.text_area(
        "Requirement (Agent Mode)",
        height=180,
        placeholder="Paste a vague requirement and let the agent ask clarifying questions..."
    )

    colA, colB = st.columns(2)
    with colA:
        if st.button("1) Generate questions"):
            if not req2.strip():
                st.warning("Please paste a requirement first.")
            else:
                with st.spinner("Generating clarifying questions..."):
                    try:
                        q = generate_clarifying_questions(req2.strip())
                        st.session_state["agent_req"] = req2.strip()
                        st.session_state["questions"] = q["clarifying_questions"]
                        st.success("Questions generated. Answer them below.")
                    except Exception as e:
                        st.error(str(e))

    questions = st.session_state.get("questions", [])
    if questions:
        st.subheader("Answer the clarifying questions")
        answers = []
        for item in questions:
            ans = st.text_input(f"{item['id']}: {item['question']}", key=f"ans_{item['id']}")
            answers.append({
                "id": item["id"],
                "question": item["question"],
                "answer": ans.strip()
            })

        if st.button("2) Improve analysis using my answers", type="primary"):
            # Keep unanswered questions too (agent should flag remaining ambiguity)
            with st.spinner("Improving analysis..."):
                try:
                    improved = improve_with_answers(st.session_state["agent_req"], answers)
                    st.session_state["improved_report"] = improved
                    render_report(improved)
                except Exception as e:
                    st.error(str(e))