# Pre-Submission Sanitization Scripts

Run these *in order* before pushing to the burner GitHub account and
before submitting the anonymous link to anonymous.4open.science.

> **Naming convention.** This staging directory is intended to be copied
> verbatim into a clean working tree outside the source repo (e.g.
> `cp -r ./* <your-staging-dir>/anon_repo/`) before pushing to the
> burner GitHub repo. The burner GitHub repo and the resulting
> anonymous.4open.science URL should also be named `anon_repo` (or
> `structagent-anon`) — English only, so the URL does not contain
> percent-encoded characters.

## Usage

```bash
# 1. Copy fresh metrics + the sample project's GT from the source repo.
#    --sample-id <project_id> = which one building is released visually.
#    Only that GT is copied; the other 19 buildings' GT is intentionally
#    withheld for consistency with the drawing-release policy.
python scripts/sanitize.py --src ../../ --dst . --sample-id 378 --strict

# 2. Audit — must return 0 hits.
python scripts/audit_anonymity.py --root .

# 3. If audit reports hits: fix and re-run (1) and (2).
```

## What `sanitize.py` does

The script auto-detects the source layout — it looks for
`experiments/eval/` and `experiments/gt/` first (the post-reorganization
layout) and falls back to `experiments/eval/` / `experiments/gt/` if
present, or to the older `paper/eval/` / `paper/gt/` if not. The first
existing directory wins; either layout works.

- Copies `experiments/eval/results/*.json` (or `paper/eval/results/`)
  → `data/metrics/` with the following replacements applied to each
  string value:
  - `E:\\Claude_cli_lab\\experiments\\gt\\`  → `data/gt/`
  - `E:\\Claude_cli_lab\\experiments\\eval\\` → `code/eval/`
  - `E:\\Claude_cli_lab\\paper\\gt\\`         → `data/gt/`  (legacy)
  - `E:\\Claude_cli_lab\\paper\\eval\\`       → `code/eval/` (legacy)
  - `E:\\lab\\exp_*\\...\\project_semantic.json` → `<SANDBOX>/<cell>/project_semantic.json`
  - any path containing `C:\\Users\\<username>\\` → `<HOME>/`
  - Skips drop-listed project ids (e.g. `81_3`, `340`).
- Copies `experiments/eval/*.py` → `code/eval/` with the same path
  replacements applied to string literals.
- Copies **only** `experiments/gt/<sample-id>.gt.json` → `data/gt/`.
  The other 19 GT files are not copied — their per-entity content
  encodes the structural skeleton of buildings whose drawings we cannot
  redistribute, so their GT is withheld for consistency with the
  drawing-release policy.

## What `audit_anonymity.py` does

Greps the entire `anon_repo/` tree for known identifying strings.
Returns non-zero exit code on any hit. Configurable via
`AUDIT_TERMS` at the top of the script.

Default terms to grep for (edit before running):

- Author real name(s) and pinyin variants
- Affiliation name (English + native script)
- City of affiliation
- Personal email + email domain
- Personal GitHub username
- Burner GitHub username **(verify it's not in the bundled files)**
- Internal sandbox roots (`E:\\lab`, `E:\\Claude_cli_lab`, `D:\\anon_release`)
- Username from the OS (`C:\\Users\\...`)
- Internal project codenames

## When to re-run

- Any time you regenerate metrics JSON (re-run sanitize).
- Any time you add a new file to `anon_repo/` (re-run audit).
- Right before pushing to burner GitHub (final audit gate).
- Right before submitting the `anonymous.4open.science` link (one more audit).
