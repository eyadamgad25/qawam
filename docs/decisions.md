# Decisions log

Append-only. Newest entry at the top. Each entry: date, task, decision, alternatives, trade-off, how to reverse.

---

## 2026-10-21 — Task 0 — Monorepo at workspace root

- **Decision:** Treat `Grad_1` as the Qawam repository root (not a nested `qawam/` folder). npm workspaces: `web/` and `api/`. Shared ESLint/Prettier/CI at root. Python lives in `ml/` + `tests/python/` with pytest, not in the npm workspace.
- **Alternatives:** (1) Nested `qawam/` directory matching the brief tree literally. (2) Separate git repos for web/api/ml.
- **Trade-off:** One repo matches a student graduation project and a single CI pipeline. Nested extra folder would fight the existing Cursor workspace path. Multiple repos would make Task 0–6 slower to review.
- **Reverse:** Move folders later; git history can follow with `git mv`.
- **UNVERIFIED:** Node 24 vs “LTS” — confirm on https://nodejs.org. Python 3.11 is specified; this machine currently has 3.14 only.
- **Follow-up:** `web/` uses TypeScript `moduleResolution: bundler` (Vite later). `api/` keeps `NodeNext` and `.js` specifiers. Local npm needed `NODE_OPTIONS=--use-system-ca`; we did not disable TLS verification.

## Template

```
## YYYY-MM-DD — Task N — Title
- Decision:
- Alternatives:
- Trade-off (examiner one-liner):
- Reverse:
```
