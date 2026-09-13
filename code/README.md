# Buy or Wait? Solution

This directory contains the AI-powered financial agent to solve the "Buy or Wait?" task.

## Architecture: Hybrid AI + Deterministic Financial Engine

This solution implements a rigorous, security-first pipeline to guarantee deterministic financial safety.

1. **Authentication & Authorization:** The frontend requires login and explicit IDOR checks to ensure users can strictly access only their own financial resources.
2. **Evidence Filtering:** Only directly relevant messages and images are passed to the AI.
3. **AI Layer (Facts ONLY):** Uses `gemini-1.5-flash` strictly to extract structured facts (`ExtractedFact`) from raw text/images. The LLM does **no** arithmetic and makes **no** financial decisions. LLM responses are cached to disk to save API quotas.
4. **Conflict Resolver:** Applies strict precedence rules (e.g., cancellations override new requests) to merge AI facts with database records.
5. **Financial State:** Reconstructs the 90-day base case (recurring income/expenses) independent of the user's specific request.
6. **Simulator & Solver:** A pure mathematical engine that safely evaluates affordability bounds across all possible payment plans without risking LLM hallucinations.
7. **Verifier:** A fail-closed mechanism that double-checks all constraints before committing a decision.

## Requirements

The solution requires Python 3.9+.

```bash
pip install -r requirements.txt
```

## Setup

Set your Gemini API key in a `.env` file at the root of the project:
```bash
GEMINI_API_KEY=your_api_key_here
```
The application relies strictly on the `.env` file to prevent frontend key leaks.

## Running the Web UI

To launch the secure web interface:
```bash
streamlit run code/app.py
```
This will open a dashboard where you must authenticate (use password `password123`). The UI is wired directly to the deterministic backend pipeline.

## Running the Evaluation (Batch)

To run the agent on the full dataset and generate `output.csv` securely:
```bash
python main.py
```
