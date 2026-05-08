# Security Policy

ATLARS deals with deeply personal data — journals, beliefs, emotional states, relationships. Security is not a feature. It is the foundation.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest (main branch) | ✅ Active support |
| Older releases | ⚠️ Critical fixes only |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report privately:

**Email:** security@thehustlehouseofficial.com  
**Subject line:** `[SECURITY] Brief description`

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Proof-of-concept if available

We will acknowledge within **48 hours** and provide a resolution timeline within **7 days**.

## What We Consider Security Issues

- Unauthorized access to another user's data
- Authentication or authorization bypass (JWT forgery, refresh token reuse without invalidation)
- Injection vulnerabilities (NoSQL injection, command injection, prompt injection)
- Exposure of API keys or secrets
- Data leakage between user namespaces (`user_id` isolation bypass)
- Vulnerabilities in the Context Compression Protocol that could corrupt or expose personal memory data
- Embedding data leakage (vector inversion attacks that reconstruct entry text)

## Responsible Disclosure

We follow coordinated disclosure. We ask that you:
- Give us reasonable time to fix before public disclosure (minimum 90 days)
- Not access or modify other users' data during research
- Not perform denial-of-service attacks

We will publicly credit all verified security researchers who report responsibly, unless you prefer to remain anonymous.

## Privacy Architecture

For contributors and users, ATLARS is designed with these guarantees:

- **User namespace isolation** — all data is partitioned by `user_id`; cross-user queries are impossible by application design
- **Full data export** — users can download their entire dataset at any time as structured JSON
- **Local-first option** — the entire stack runs on-device with no cloud dependency
- **Encryption at rest** — Atlas deployments encrypt by default; self-hosted deployments should use encrypted volumes
- **JWT security** — access tokens in in-memory module variable (never persisted), refresh tokens in `expo-secure-store` (iOS Keychain / Android Keystore encrypted storage)
