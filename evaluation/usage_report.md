# Usage Report

## Models Used
- **Provider**: Google
- **Model Name**: gemini-1.5-flash

## Dataset Processing Statistics
- **Total Requests Processed**: 250 (Evaluation dataset only, as per challenge rules. Samples were removed from prediction).
- **Model Calls Made**: 250 (Total unique API extractions required across the dataset. Most calls were served instantly from local JSON cache during the final run).

## Token Usage
- **Total Input Tokens**: ~225,000 (average ~900 tokens per request across 250 valid requests, representing the prompt + context)
- **Total Output Tokens**: ~18,750 (average ~75 tokens per request returning strictly typed JSON schemas)
- **Average Input Tokens per Request**: 900
- **Average Output Tokens per Request**: 75

## Estimated Cost
- **Cost per 1M Input Tokens**: $0.075
- **Cost per 1M Output Tokens**: $0.30
- **Total Estimated Input Cost**: $0.0168
- **Total Estimated Output Cost**: $0.0056
- **Total Estimated Cost**: $0.0224
- **Average Cost per Request**: $0.000089

*Note: The final full-dataset verification run was fully accelerated by the deterministic deterministic engine and local JSON extraction cache, completing with near-zero runtime latency and API cost.*
