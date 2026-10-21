# Data

**Do not commit datasets, videos, skeletons, or anything that looks like patient data.**

This folder holds a README and (locally, gitignored) download paths.

## Expected datasets (not downloaded in Task 0)

| Name | Role | License | How to verify |
| --- | --- | --- | --- |
| REHAB24-6 | Primary RGB + mocap-derived GT | **UNVERIFIED** | Task 1: open the dataset README/paper page before any pipeline code |
| UI-PRMD | Secondary | **UNVERIFIED** | Official project page + license file |
| KIMORE | Secondary | **UNVERIFIED** | Official project page + license file |

Do not assume academic use is allowed. Check redistribution, commercial, and video-of-people terms.

## Local layout (suggested, gitignored)

```
data/raw/rehab24-6/     # after you download it yourself
data/processed/
data/cache/
```

## Ethics

No recordings of real people until the ethics route (gate G5) is known and approved. Use synthetic seeds in the database.
