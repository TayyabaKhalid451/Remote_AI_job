# RemoteAI Jobs

A Streamlit remote-job finder that retrieves listings from the Adzuna API, then ranks and explains them with transparent matching and risk indicators. Groq is optional and is restricted to career analysis of the job records already retrieved.

## What it does

- Searches real Adzuna listings using a remote-focused query. It never makes up jobs, companies, salary figures, or application URLs.
- Scores a candidate/job fit using detected skills, selected field, and experience-level language.
- Shows an explainable authenticity/risk indicator: HTTPS URL, source provenance, employer/date presence, and scam-language flags. This is not a guarantee—users must still verify the employer and never pay to apply.
- Builds a ranked skill-gap view from returned job descriptions and core field skills.
- Optionally asks Groq for a grounded career summary; the prompt explicitly forbids inventing job listings or facts.

## Local setup

1. Create an [Adzuna developer account](https://developer.adzuna.com/) and get an app ID and key. Groq is optional; obtain its key from [GroqCloud](https://console.groq.com/keys).
2. Clone this repository, then install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create `.streamlit/secrets.toml` (it is ignored by Git):

   ```toml
   ADZUNA_APP_ID = "your_adzuna_app_id"
   ADZUNA_APP_KEY = "your_adzuna_app_key"
   GROQ_API_KEY = "your_optional_groq_key"
   # Optional: GROQ_MODEL = "llama-3.3-70b-versatile"
   ```

   Environment variables with the same names also work locally.
4. Start it:

   ```bash
   streamlit run app.py
   ```

Without Adzuna credentials the interface remains usable but deliberately shows no example listings.

## Deploy to Streamlit Community Cloud

1. Create a GitHub repository and commit these files; do **not** commit `.streamlit/secrets.toml` or `.env`.
2. In Streamlit Community Cloud, select **Create app**, select the repository and branch, and use `app.py` as the main file.
3. In the app’s **Settings → Secrets**, paste the TOML keys shown above, then deploy/reboot.
4. Test a search and the original-listing link. Confirm that the country markets you expose match your Adzuna API access.

## Project layout

```
app.py                         # Streamlit interface
core/matcher.py                # skill parsing, matching, gaps
services/job_service.py        # Adzuna retrieval only
services/verification_service.py # explainable risk indicators
services/groq_service.py       # optional grounded Groq analysis
prompts/job_analysis_prompt.txt
```

## Practical limitations

Adzuna is an aggregator, so an API response and score cannot prove that an offer is legitimate or still open. The app keeps the original URL visible, flags suspicious language, and calls the result an indicator rather than “verified.” For a stronger production system, add direct company career-page sources (e.g., ATS feeds) and employer-domain verification with an auditable provenance record.
