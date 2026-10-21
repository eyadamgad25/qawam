# Data

**Do not commit datasets, videos, skeletons, or anything that looks like patient data.**

This folder holds a README and (locally, gitignored) download paths.

## Datasets

| Name | Role | License | How to verify |
| --- | --- | --- | --- |
| REHAB24-6 | Primary RGB + 2D joints + repetition CSV | Zenodo custom: academic / non-profit non-commercial research only (their spelling “noncomercial”); cite SISAP 2024 paper; commercial → info@visioncraft.ai. Quoted 2026-10-21 from https://zenodo.org/records/13305826 | `docs/dataset-report.md` |
| UI-PRMD | Secondary | **UNVERIFIED** | Official project page + license file |
| KIMORE | Secondary | **UNVERIFIED** | Official project page + license file |

UI-PRMD / KIMORE: do not assume academic use is allowed until their license files are read. REHAB24-6 terms are in `docs/dataset-report.md`. Never commit `data/raw/`.

## Local layout (suggested, gitignored)

```
data/raw/rehab24-6/     # after you download it yourself
data/processed/
data/cache/
```

## Ethics

No recordings of real people until the ethics route (gate G5) is known and approved. Use synthetic seeds in the database.
