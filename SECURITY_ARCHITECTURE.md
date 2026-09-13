# Security Architecture
## 1. Authentication
Uses Argon2id via `passlib` or `argon2-cffi`. Password hashes are stored securely. 

## 2. Authorization (IDOR Prevention)
The `SecurityContext` enforces that the `authenticated_user_id` strictly matches the `dataset_user_id` of the requested resource.

## 3. Evidence Isolation
LLM facts are strictly filtered. The AI only processes events relevant to the explicitly requested User ID.

## 4. Fail-Closed
If ANY data is missing, corrupted, or cannot be verified, the backend safely defaults to `not_affordable`.
