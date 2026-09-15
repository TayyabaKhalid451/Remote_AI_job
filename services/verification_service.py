"""Explainable listing authenticity and risk indicators; not a guarantee of legitimacy."""
from __future__ import annotations

from urllib.parse import urlparse

RISK_PHRASES = ("pay to apply", "registration fee", "wire transfer", "bitcoin", "crypto payment", "telegram only", "whatsapp only")
CAUTION_PHRASES = ("urgent hiring", "no experience necessary", "guaranteed income", "act now")


def assess_job(job: dict) -> dict:
    url = str(job.get("url", ""))
    parsed = urlparse(url)
    text = (str(job.get("title", "")) + " " + str(job.get("description", ""))).lower()
    reasons, score = [], 35
    if parsed.scheme == "https" and parsed.netloc:
        score += 25; reasons.append("Uses a secure, non-empty application URL")
    else:
        reasons.append("Application URL is missing or not secure")
    if job.get("source") == "Adzuna":
        score += 25; reasons.append("Retrieved from the Adzuna job-search API")
    if job.get("company") and job["company"] != "Not supplied":
        score += 10; reasons.append("Company name was supplied by the source")
    if job.get("created"):
        score += 5; reasons.append("Posting date was supplied by the source")
    flags = [phrase for phrase in RISK_PHRASES if phrase in text]
    cautions = [phrase for phrase in CAUTION_PHRASES if phrase in text]
    score -= 35 * len(flags) + 10 * len(cautions)
    if flags: reasons.append("High-risk language detected: " + ", ".join(flags))
    if cautions: reasons.append("Cautionary language detected: " + ", ".join(cautions))
    score = max(0, min(100, score))
    label = "Higher confidence" if score >= 75 else "Review carefully" if score >= 50 else "Higher risk"
    return {"score": score, "label": label, "reasons": reasons, "risk_flags": flags + cautions}
