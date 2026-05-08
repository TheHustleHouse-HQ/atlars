# Governance

ATLARS is an open-source project maintained by The Hustle House. This document defines who controls what, how decisions are made, and what contributors can expect.

## Project Ownership

**The Hustle House** owns the ATLARS trademark, brand, and the hosted cloud product. The code is open-source under Apache 2.0 — meaning anyone can fork, self-host, and build on top of it — but the company retains full control over:

- What gets merged into `main`
- The roadmap and feature priorities
- The contributor program and certificate issuance
- The cloud-hosted product
- The official brand, logo, and name

## Decision Making

This is **not** a consensus-driven project. The lead maintainer ([@thhteamspace](https://github.com/thhteamspace)) has final say on all technical and product decisions. Contributors are encouraged to propose, debate, and advocate — but the maintainer's decision is final once made.

This is standard for founder-led open-source projects. It ensures a strong vision and prevents committee design.

## What Contributors Control

Once a contributor's PR is merged, they have full credit for that contribution. The contributor program milestone it unlocks is guaranteed if the criteria are met. Maintainers cannot revoke earned certificates.

Contributors do **not** have voting rights on roadmap decisions, repository settings, or project governance.

## Merge Authority

| Role | Who | Can merge? |
|------|-----|-----------|
| Lead Maintainer | [@thhteamspace](https://github.com/thhteamspace) | ✅ Yes, to any branch |
| Trusted Contributor | Assigned by lead | ✅ Yes, to `develop` only |
| Contributor | Any merged PRs | ❌ No |

## Branch Protection Rules

`main` branch:
- Require at least 1 approving review from a maintainer
- All CI checks must pass
- No force pushes
- No direct commits — all changes via PR

`develop` branch:
- Requires CI to pass
- Can be approved by Trusted Contributors
- Merges to `main` via PR from lead maintainer only

## Trusted Contributor Status

After consistent, high-quality contributions over several months, the lead maintainer may grant Trusted Contributor status. This gives:

- Merge rights to `develop`
- Input on roadmap priorities (advisory, not voting)
- Priority consideration for internship roles

Given at the lead maintainer's sole discretion. Can be revoked.

## Forking Policy

You are free to fork ATLARS. If you do:
- Retain the Apache 2.0 license and copyright notice
- Do not use the "ATLARS" name or logo for a competing product
- Do not imply endorsement by The Hustle House
- You are encouraged to contribute improvements back via PR

## CLA (Contributor License Agreement)

By submitting a PR, you agree that:

1. Your contribution is your original work
2. You have the right to submit it under the Apache 2.0 license
3. You grant The Hustle House a perpetual license to use, modify, and distribute your contribution as part of ATLARS
4. You understand that your contribution does not grant you any ownership rights in ATLARS or The Hustle House

---

*Questions about governance can be raised in GitHub Discussions.*
