"""Optional Groq analysis. It may summarize supplied data, never create job listings or URLs."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _key(secrets: Any | None = None) -> str | None:
    if secrets:
        try:
            value = secrets.get("GROQ_API_KEY")
            if value: return str(value)
        except Exception: pass
    return os.getenv("GROQ_API_KEY")


def is_configured(secrets: Any | None = None) -> bool:
    return bool(_key(secrets))


def analyze_jobs(field: str, level: str, user_skills: list[str], jobs: list[dict], gaps: list[dict], secrets: Any | None = None) -> str:
    api_key = _key(secrets)
    if not api_key:
        raise RuntimeError("Groq is not configured.")
    from groq import Groq
    template = Path(__file__).resolve().parents[1] / "prompts" / "job_analysis_prompt.txt"
    prompt = template.read_text(encoding="utf-8").format(field=field, level=level,
        user_skills=", ".join(user_skills) or "not provided", jobs=[{"title": j["title"], "company": j["company"], "skills": j.get("match", {}).get("required_skills", []), "score": j.get("match", {}).get("score")} for j in jobs[:12]], gaps=gaps[:8])
    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": prompt}], temperature=0.2, max_tokens=700)
    return completion.choices[0].message.content or "No analysis returned."
