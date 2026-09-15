"""Job retrieval. This service returns only records supplied by a real source."""
from __future__ import annotations

import html
import os
import re
from typing import Any

import requests

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"


class JobSourceError(RuntimeError):
    pass


def _setting(name: str, secrets: Any | None = None) -> str | None:
    if secrets:
        try:
            value = secrets.get(name)
            if value:
                return str(value)
        except Exception:
            pass
    return os.getenv(name)


def adzuna_is_configured(secrets: Any | None = None) -> bool:
    return bool(_setting("ADZUNA_APP_ID", secrets) and _setting("ADZUNA_APP_KEY", secrets))


def _clean_description(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def search_adzuna(query: str, country: str, employment_type: str, page: int = 1,
                  results_per_page: int = 30, secrets: Any | None = None) -> tuple[list[dict[str, Any]], int]:
    """Search Adzuna. Raises an actionable error rather than creating synthetic listings."""
    app_id = _setting("ADZUNA_APP_ID", secrets)
    app_key = _setting("ADZUNA_APP_KEY", secrets)
    if not app_id or not app_key:
        raise JobSourceError("Adzuna credentials are not configured. Add ADZUNA_APP_ID and ADZUNA_APP_KEY to Streamlit secrets.")
    country_code = (country or "gb").lower()
    params = {"app_id": app_id, "app_key": app_key, "what": query, "results_per_page": results_per_page,
              "content-type": "application/json"}
    if employment_type and employment_type != "Any":
        params["full_time"] = "1" if employment_type == "Full-time" else "0"
    try:
        response = requests.get(f"{ADZUNA_BASE_URL}/{country_code}/search/{page}", params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise JobSourceError(f"Adzuna could not be reached: {exc}") from exc
    jobs = []
    for item in payload.get("results", []):
        redirect_url = item.get("redirect_url")
        if not redirect_url:
            continue
        jobs.append({
            "id": f"adzuna:{item.get('id')}", "title": item.get("title", "Untitled role"),
            "company": (item.get("company") or {}).get("display_name", "Not supplied"),
            "location": (item.get("location") or {}).get("display_name", "Not supplied"),
            "description": _clean_description(item.get("description", "")), "url": redirect_url,
            "created": item.get("created", ""), "salary_min": item.get("salary_min"),
            "salary_max": item.get("salary_max"), "category": (item.get("category") or {}).get("label", ""),
            "source": "Adzuna", "remote_claim": "remote" in (item.get("title", "") + " " + item.get("description", "")).lower(),
        })
    return jobs, int(payload.get("count", len(jobs)))
