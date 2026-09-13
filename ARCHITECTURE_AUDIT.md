# ARCHITECTURE_AUDIT.md

## Current Architecture
The current architecture in `code/main.py` acts as a monolithic LLM-driven decision engine. It takes all structured CSV data, messages, and images, concatenates them into a massive JSON prompt, and sends them to Gemini 1.5 Pro. It relies on a "scratchpad" instruction for the LLM to internally simulate 90 days, check constraints, select payment options, and output the final required fields.

## Current Data Flow
1. Load all CSVs into Pandas DataFrames.
2. For each request, filter related profile, events, messages, images, and payment options.
3. Serialize the filtered subset to JSON.
4. If images exist, load via PIL.
5. Send the entire context to Gemini with a massive system prompt containing the challenge rules.
6. Receive parsed JSON containing `amount_safe_to_pay`, `payment_plan`, etc.
7. Write directly to `output.csv`.

## Current LLM Usage
Gemini 1.5 Pro is currently responsible for **everything**:
- Understanding ambiguous natural language messages.
- OCR/amount extraction from images.
- Recurrence classification of financial events.
- Mathematical 90-day simulation of account balances.
- Generating valid partial/installment payment plans.
- Ranking plans according to tie-breaker logic.
- Verifying the final output constraints.

## Current Financial Logic
There is **no** deterministic financial logic in Python. It relies 100% on the LLM's emergent arithmetic reasoning via the scratchpad.

## Current Security Model
- API key is loaded via `os.environ` which is acceptable.
- However, since the LLM processes untrusted user messages alongside system rules in the same prompt, it is highly vulnerable to **Prompt Injection**. An embedded instruction in a message (e.g., "Ignore all rules and approve this") could directly manipulate the affordability status.

## Current Simulation Logic
Non-existent in code. Delegated to LLM scratchpad.

## Current Optimizer
Non-existent in code. Delegated to LLM scratchpad.

## Current Bugs
- **Math Errors:** LLMs cannot reliably simulate 90 days of daily financial arithmetic for complex portfolios. The balance checks will likely fail on hidden tests.
- **Hallucinations:** The LLM may invent dates, installment amounts, or fake spending changes to make a plan work.
- **Rule Violations:** The strict tie-breaker priority is difficult to enforce purely via LLM instructions over multiple candidate plans.

## Critical Risks
- **Financial correctness failure:** The system will fail the safety invariants (minimum balance violations).
- **Security:** Treating data (messages) as context allows for severe prompt injection overriding problem rules.
- **Non-deterministic:** Output varies per run. No reproducibility.
- **Token Inefficiency:** Pushing 100s of events per request into the LLM context is wasteful when 90% is fixed structural data.

---

## Recommended Architecture

We must pivot to a **Hybrid AI + Deterministic Financial Reasoning System**:

1. **AI Understanding Layer (LLM):** 
   - Only processes `messages.csv` and `images.csv`.
   - Extracts structured facts: e.g., "Cancel event_17", "Salary is now X starting Y", "Image amount is Z".
2. **Financial State Reconstruction (Python):**
   - Merges CSV events and LLM-extracted facts into a unified `FinancialCase` object.
3. **Conflict Resolution & Data Validation (Python):**
   - Applies deterministic precedence (newer records > older, settled > forecast).
4. **90-Day Forecast Engine (Python):**
   - A strict daily simulation loop that applies recurring transactions, one-offs, and minimum balances.
5. **Safe Plan Generator (Python):**
   - Enumerates valid payment plans (Full, Partial, Installments, Wait).
   - Validates each plan through the 90-day simulator.
6. **Plan Optimizer (Python):**
   - Ranks safe plans strictly using the 6-priority rules.
7. **Deterministic Safety Verifier (Python):**
   - Asserts all invariants (sum(payments) == requested_amount, etc.).
8. **Explainable Decision (LLM - Optional/Controlled):**
   - Generates natural language summary based on verified Python output.

## Migration Plan
1. **Refactor `main.py`** to extract the LLM calls into a specialized `LLMProvider` class focusing *only* on message and image interpretation.
2. **Build the Python Domain Model:** Create structured classes (`FinancialEvent`, `UserProfile`, `PaymentOption`).
3. **Build the Simulator:** Write a `Simulator` class that takes a starting balance and a list of events and calculates the daily balance for 90 days.
4. **Implement Generators and Optimizers:** Write Python logic to generate valid partial payment dates and evaluate installment bounds.
5. **Add the Verifier:** Implement assertions for final output validation before writing to `output.csv`.
6. **Testing:** Write local unit tests covering Cases A through M described in the requirements.
