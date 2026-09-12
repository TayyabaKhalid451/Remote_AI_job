"""Transparent, deterministic job and skills matching utilities."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any


# This deliberately stays curated and explainable; it is not an LLM inference.
SKILL_LIBRARY: dict[str, list[str]] = {
    "software development": ["python", "javascript", "git", "sql", "rest api", "docker", "aws"],
    "data science": ["python", "sql", "statistics", "pandas", "machine learning", "data visualization"],
    "ai/ml": ["python", "machine learning", "pytorch", "tensorflow", "sql", "statistics", "docker"],
    "cybersecurity": ["networking", "linux", "python", "siem", "incident response", "security"],
    "ui/ux": ["figma", "user research", "wireframing", "prototyping", "design systems"],
    "digital marketing": ["seo", "google analytics", "content marketing", "social media", "copywriting"],
    "accounting": ["excel", "bookkeeping", "financial reporting", "quickbooks", "reconciliation"],
    "human resources": ["recruiting", "onboarding", "hris", "employee relations", "communication"],
}

LEVEL_TERMS = {
    "Beginner": ("junior", "entry", "intern", "graduate", "associate", "0-2 years"),
    "Intermediate": ("mid", "3+ years", "2+ years", "experienced", "specialist"),
    "Advanced": ("senior", "lead", "principal", "staff", "manager", "director"),
}


def normalize_skill(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def parse_skills(raw: str | list[str] | None) -> list[str]:
    if isinstance(raw, list):
        tokens = raw
    else:
        tokens = re.split(r"[,;\n]", raw or "")
    return list(dict.fromkeys(normalize_skill(t) for t in tokens if normalize_skill(t)))


def recommended_skills(field: str, level: str) -> list[str]:
    field_key = normalize_skill(field)
    base = SKILL_LIBRARY.get(field_key, ["communication", "time management", "collaboration", "problem solving"])
    limit = {"Beginner": 4, "Intermediate": 6, "Advanced": len(base)}.get(level, 5)
    return base[:limit]


def extract_skills(text: str, field: str = "") -> list[str]:
    searchable = normalize_skill(text)
    vocabulary = set(recommended_skills(field, "Advanced"))
    vocabulary.update(skill for skills in SKILL_LIBRARY.values() for skill in skills)
    # useful cross-field terms that appear frequently in job descriptions
    vocabulary.update({"agile", "scrum", "excel", "react", "typescript", "fastapi", "communication"})
    return sorted(skill for skill in vocabulary if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", searchable))


def job_match(job: dict[str, Any], field: str, level: str, user_skills: list[str]) -> dict[str, Any]:
    text = " ".join(str(job.get(k, "")) for k in ("title", "description", "category"))
    text_l = normalize_skill(text)
    desired = recommended_skills(field, level)
    required = job.get("skills") or extract_skills(text, field)
    user = set(user_skills)
    overlap = sorted(set(required) & user)
    missing = sorted(set(required) - user)

    field_hits = sum(1 for skill in desired if skill in text_l)
    skill_score = (len(overlap) / max(1, len(required))) * 55
    field_score = (field_hits / max(1, len(desired))) * 25
    level_score = 20 if any(term in text_l for term in LEVEL_TERMS.get(level, ())) else 10
    score = min(100, round(skill_score + field_score + level_score))
    return {"score": score, "matched_skills": overlap, "missing_skills": missing, "required_skills": required}


def skill_gap(jobs: list[dict[str, Any]], field: str, level: str, user_skills: list[str]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter(recommended_skills(field, level))
    user = set(user_skills)
    for job in jobs:
        counts.update(skill for skill in job.get("match", {}).get("required_skills", []) if skill not in user)
    return [{"skill": skill, "demand": count, "status": "You have it" if skill in user else "Gap"}
            for skill, count in counts.most_common(10)]
