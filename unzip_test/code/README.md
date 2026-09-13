# Buy or Wait? Solution

This directory contains the AI-powered financial agent to solve the "Buy or Wait?" task.

## Requirements

The solution uses the `google-genai` SDK and the `gemini-1.5-pro` model to evaluate requests, taking advantage of its large context window and multimodal capabilities to process images, messages, and raw transaction data end-to-end.

To install dependencies:
```bash
pip install -r requirements.txt
```

## Setup

Set your Gemini API key in the environment variables:
```bash
# On Windows PowerShell
$env:GEMINI_API_KEY="your_api_key_here"

# On Linux/macOS
export GEMINI_API_KEY="your_api_key_here"
```

## Running the Frontend UI

To launch the secure, trustworthy web interface for the AI agent:
```bash
streamlit run app.py
```
This will open a dashboard in your browser where you can select a request, securely enter your API key, and view the AI's step-by-step reasoning and affordability recommendation.

## Running the Evaluation (Batch)

To run the agent and generate `output.csv` (which will be placed in the `dataset/` directory) and the token usage report (placed in `code/evaluation/`):
```bash
python main.py
```

## Architecture

The system groups all historical events, future scheduled events, messages, images, payment options, and the user profile for each request and formats them into a comprehensive prompt. 

It passes this context along with the strict rules to `gemini-1.5-pro`. The model uses a JSON output schema with a scratchpad to write out a 90-day balance forecast and select the optimal payment plan based on the tie-breaking logic.
