# AUDIT REPORT
## 1. Current Architecture
The current architecture implements a basic data pipeline consisting of UI (`app.py`), LLM Extractor (`llm.py`), Conflict Resolver (`resolver.py`), Financial State (`state.py`), Simulator (`simulator.py`), Solver (`solver.py`), Optimizer (`optimizer.py`), and Verifier (`verifier.py`). Data flows from the CSV dataset into the Python engine. 

## 2. Current Data Flow
1. User selects a `request_id`.
2. System loads relevant `FinancialProfile`, `FinancialEvent`s, `Message`s, `Image`s.
3. `LLMProvider` extracts structured facts from messages and images using Gemini.
4. `ConflictResolver` merges extracted facts with raw database events.
5. `FinancialStateLayer` infers 90-day recurring events (incomes/expenses) from historical events.
6. `Simulator` traces day-by-day balances over 90 days.
7. `Solver` tests payment plans against the Simulator to find valid ones.
8. `Optimizer` ranks the valid plans based on challenge rules.
9. `Verifier` double-checks the top plan constraints.
10. UI displays the result.

## 3. Security Vulnerabilities
- **Authentication:** `password123` hardcoded authentication mechanism is completely insecure.
- **Session Management:** Using plain `st.session_state` without strict UUID enforcement allows easy manipulation.
- **IDOR / Resource Ownership:** IDOR protection relies strictly on `req_row['user_id'] == current_user` but doesn't prevent data bleeding if parameters are spoofed or queries are unparameterized (though CSVs are currently loaded into Pandas).
- **Gemini Key Exposure:** No active key exposure to UI, but requires formal `.env` management.
- **LLM Prompt Injection:** System prompts lack explicit safety bounds prioritizing financial rules over message instructions.

## 4. Financial Correctness Risks
- **Double Counting:** Historical forecasted events might be double-counted against explicit scheduled events.
- **Currency Conversion:** `exchange_rates.csv` is not yet utilized in the Simulator.
- **Event Statuses:** `pending`, `failed`, `cancelled` transactions may not be completely filtered out of available cash.
- **Spending Changes:** Flexible expense reduction is completely unhandled (`none` is hardcoded).

## 5. Dataset / Schema Assumptions
- Current system assumes all users have messages and images (they don't).
- Current system assumes dates are perfectly formatted ISO strings.

## 6. UI Problems
- Prototype UI lacks professional fintech layout.
- "No requests found" triggers blindly when `user_01` has no requests instead of a polite empty state.
- Exposes raw variable states rather than a verified decision card.

## 7. LLM Risks
- Untrusted LLM output could hallucinate invalid JSON or facts.
- Quota exhaustion without graceful degradation (if LLM fails, system crashes).
- Cross-user cache contamination if cache keys ignore user IDs.

## 8. Missing Challenge Requirements
- Proper currency conversions via `exchange_rates.csv`.
- Proper flexible spending modifications (`spending_changes_needed`).
- Proper handling of explicitly requested exact `payment_options`.

## 9. Files That Need Modification
- `code/app.py` (Massive UI upgrade)
- `code/llm.py` (Strict Schema, Error Handling)
- `code/resolver.py` (Precedence Rules)
- `code/simulator.py` (Currency, Status filtering)
- `code/solver.py` (Spending Changes)
- `code/state.py` (Double-counting fixes)
- `main.py` (Pipeline adjustments)

## 10. New Files Required
- `code/auth.py` (Argon2id implementation)
- `code/data_loader.py` (Abstracted data access with IDOR bounds)
- `code/evidence_processor.py` (Relevance Filtering)
- `code/explanation.py` (Deterministic Explanations)
- `code/security.py` (Security utilities)
- `SECURITY_ARCHITECTURE.md`
- `SECURITY_TEST_REPORT.md`
- 11 new automated test files in `tests/`
