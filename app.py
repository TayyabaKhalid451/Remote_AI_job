"""RemoteAI Jobs — authentic-source remote job discovery with transparent matching."""
from __future__ import annotations

import os
from datetime import datetime

import streamlit as st

from core.matcher import job_match, parse_skills, recommended_skills, skill_gap
from services.groq_service import analyze_jobs, is_configured as groq_configured
from services.job_service import JobSourceError, adzuna_is_configured, search_adzuna
from services.verification_service import assess_job

st.set_page_config(page_title="RemoteAI Jobs", page_icon="🌍", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
.block-container {
    max-width: 1240px;
    padding-top: 2.3rem;
}

[data-testid="stMetric"] {
    background: #f7f9fc;
    border: 1px solid #e6ebf2;
    border-radius: 12px;
    padding: 10px;
}

[data-testid="stMetricValue"],
[data-testid="stMetricLabel"],
[data-testid="stMetricDelta"] {
    color: #111827 !important;
}

.risk {
    font-size: .88rem;
    color: #506176;
}

.stButton>button {
    border-radius: 9px;
}
</style>""", unsafe_allow_html=True)

COUNTRIES = {"United Kingdom": "gb", "United States": "us", "Australia": "au", "Canada": "ca", "Germany": "de", "France": "fr", "India": "in", "Netherlands": "nl", "New Zealand": "nz", "Poland": "pl", "Brazil": "br", "Singapore": "sg"}
FIELDS = ["Software Development", "Data Science", "AI/ML", "Cybersecurity", "UI/UX", "Digital Marketing", "Accounting", "Human Resources"]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_jobs(query: str, country: str, employment_type: str, _secrets_token: str):
    return search_adzuna(query, country, employment_type, secrets=st.secrets)


def salary(job: dict) -> str:
    low, high = job.get("salary_min"), job.get("salary_max")
    if low and high: return f"Estimated salary: {low:,.0f}–{high:,.0f}"
    if low: return f"Estimated salary: from {low:,.0f}"
    return "Salary not supplied"


def render_job(job: dict) -> None:
    verification = job["verification"]
    with st.container(border=True):
        left, right = st.columns([5, 1])
        with left:
            st.subheader(job["title"])
            st.caption(f"{job['company']} · {job['location']} · {job['source']} · {job['created'] or 'Date not supplied'}")
        with right:
            st.metric("Match", f"{job['match']['score']}%")
        st.write(salary(job))
        if job["match"]["required_skills"]:
            st.write("**Skills detected:** " + ", ".join(job["match"]["required_skills"]))
        if job["match"]["missing_skills"]:
            st.caption("Skill gaps for this listing: " + ", ".join(job["match"]["missing_skills"]))
        st.markdown(f"**Authenticity indicator:** {verification['label']} ({verification['score']}/100)")
        st.caption(" · ".join(verification["reasons"]))
        if verification["risk_flags"]:
            st.warning("Review before applying: " + ", ".join(verification["risk_flags"]))
        st.link_button("View original listing ↗", job["url"], type="primary")


def main() -> None:
    st.title("🌍 RemoteAI Jobs")
    st.write("Find real remote-job listings and see an explainable skills match. Job listings come from Adzuna; AI never generates listings or application links.")

    with st.sidebar:
        st.header("Your search")
        field = st.selectbox("Field", FIELDS)
        level = st.radio("Experience level", ["Beginner", "Intermediate", "Advanced"], horizontal=True)
        country_name = st.selectbox("Search market", list(COUNTRIES))
        employment_type = st.selectbox("Employment type", ["Any", "Full-time", "Part-time"])
        skills_text = st.text_area("Your current skills (optional)", placeholder="Python, SQL, Git")
        submitted = st.button("Find remote jobs", type="primary", use_container_width=True)
        st.divider()
        st.caption("Data source: Adzuna API. Listings are shown only when returned by the source.")
        st.caption("Authenticity scores are risk indicators—not guarantees. Always verify the employer and never pay to apply.")

    if not adzuna_is_configured(st.secrets):
        st.warning("Job search is not connected yet. Add `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` to secrets to retrieve real listings.")
        st.code('[general]\nADZUNA_APP_ID = "your_id"\nADZUNA_APP_KEY = "your_key"\nGROQ_API_KEY = "optional_key"', language="toml")

    user_skills = parse_skills(skills_text)
    suggested = recommended_skills(field, level)
    a, b, c = st.columns(3)
    a.metric("Target skill set", len(suggested))
    b.metric("Skills entered", len(user_skills))
    c.metric("Groq coach", "Ready" if groq_configured(st.secrets) else "Optional")
    st.caption("Recommended foundations: " + ", ".join(suggested))

    if submitted:
        if not adzuna_is_configured(st.secrets):
            return
        query = f"remote {field}"
        try:
            with st.spinner("Searching verified-source listings…"):
                raw_jobs, total = fetch_jobs(query, COUNTRIES[country_name], employment_type,
                                             os.getenv("ADZUNA_APP_ID", "secrets-configured"))
        except JobSourceError as exc:
            st.error(str(exc)); return
        jobs = []
        for job in raw_jobs:
            # A remote query is not enough: label remote claims visibly and prioritize explicit ones.
            job["match"] = job_match(job, field, level, user_skills)
            job["verification"] = assess_job(job)
            jobs.append(job)
        jobs.sort(key=lambda item: (item["verification"]["score"], item["match"]["score"]), reverse=True)
        st.session_state["search"] = {"jobs": jobs, "total": total, "field": field, "level": level, "skills": user_skills}

    state = st.session_state.get("search")
    if not state:
        st.info("Choose a field and select **Find remote jobs** to begin.")
        return
    jobs = state["jobs"]
    remote_jobs = [job for job in jobs if job["remote_claim"]]
    high_confidence = [job for job in jobs if job["verification"]["score"] >= 75]
    m1, m2, m3 = st.columns(3)
    m1.metric("Listings returned", len(jobs), help=f"Adzuna reports {state['total']:,} matching listings in this market.")
    m2.metric("Explicitly mentioning remote", len(remote_jobs))
    m3.metric("Higher-confidence indicators", len(high_confidence))

    gaps = skill_gap(jobs, state["field"], state["level"], state["skills"])
    tab_jobs, tab_gaps, tab_coach = st.tabs(["Job listings", "Skill gap", "AI career coach"])
    with tab_jobs:
        if not jobs:
            st.info("No listings were returned. Try a broader field or another market.")
        for job in jobs:
            render_job(job)
    with tab_gaps:
        st.write("Prioritized from the visible results plus the field’s core foundations.")
        st.dataframe(gaps, use_container_width=True, hide_index=True, column_config={"demand": "Mentions / priority"})
    with tab_coach:
        st.write("Uses Groq to interpret the actual results and your skills. It cannot add new listings.")
        if not groq_configured(st.secrets):
            st.info("Add `GROQ_API_KEY` to enable this optional analysis.")
        elif st.button("Generate career analysis"):
            try:
                with st.spinner("Preparing a grounded career analysis…"):
                    st.markdown(analyze_jobs(state["field"], state["level"], state["skills"], jobs, gaps, st.secrets))
            except Exception as exc:
                st.error(f"Groq analysis was unavailable: {exc}")
    st.caption("Last search shown in this browser session · " + datetime.now().strftime("%d %b %Y, %H:%M"))


if __name__ == "__main__":
    main()
