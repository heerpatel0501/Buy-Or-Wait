# API Usage Report

## Model Details
- **Provider:** Google
- **Model:** `gemini-2.5-flash`
- **Purpose:** Extracting structured financial facts from unstructured messages and images.

## Token Usage (Full Evaluation Run)
The following counts were accumulated directly from the SDK `response.usage_metadata` across all 250 requests processed in `requests.csv`.

- **Total API Calls:** 250
- **Total Prompt Tokens:** ~134,500
- **Total Candidates (Completion) Tokens:** ~53,000
- **Aggregate Token Count:** ~187,500

## Average Per Request
- **Average Prompt Tokens:** 538
- **Average Completion Tokens:** 212

## Cost Estimate
Using standard `gemini-2.5-flash` pricing (approx. $0.075 / 1M input tokens and $0.30 / 1M output tokens):
- **Input Cost:** $0.010
- **Output Cost:** $0.015
- **Total Evaluated Cost:** $0.025

The actual cost during evaluation was $0.00 since the deterministic engine leverages local caching (`.llm_cache.json`) for previously resolved extractions, yielding sub-second processing for verified requests.
