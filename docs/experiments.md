# Experiments log

Append-only. Newest entry at the top. Record what was run, on what data, and the outcome. No clinical claims.

---

## 2026-10-21 — Task 0 — Scaffold smoke

- **Hypothesis:** Root lint, typecheck, JS unit tests, and pytest (scaffold only) pass on a clean install.
- **Setup:** Empty workspace → repo skeleton. Node v24.18.1, npm 11.16.0. Python 3.11 **not installed locally** (py reports 3.14.0). CI targets Python 3.11.
- **Command:** `npm install && npm run typecheck && npm run lint && npm run format:check && npm test` and `py -3.14 -m pytest` (local fallback; 3.11 preferred).
- **Data:** none.
- **Result:** After `$env:NODE_OPTIONS='--use-system-ca'` (local TLS intercept; GitHub Actions should not need this): `npm install` OK. After import-path + Prettier fixes: `typecheck`, `lint`, `format:check` pass; `npm test` 4 passed (web 2, api 2); `py -3.14 -m pytest` 1 passed. pytest **9.1.1** (Scripts folder not on PATH — always use `py -3.14 -m pytest`). Python 3.11 still missing locally.
- **Next:** Task 1 — REHAB24-6 license/structure check; no pipeline code until that report exists.

## Template

```
## YYYY-MM-DD — Task / experiment title
- Hypothesis:
- Setup (OS, versions, commit):
- Command:
- Data (id, split, N — never commit files):
- Metrics:
- Result:
- Caveats / UNVERIFIED:
```
