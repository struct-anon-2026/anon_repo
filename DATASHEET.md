# Datasheet — StructAgent Evaluation Set

Following Gebru et al., *Datasheets for Datasets* (CACM 2021).
For paper reviewers: this is the concise reference; the paper § 5.1 cites it.

---

## 1. Motivation

**For what purpose was the dataset created?**
To evaluate end-to-end performance of a multimodal agent (StructAgent) on
the task of reconstructing finite-element-ready frame representations from
scanned structural blueprint sheets. No prior benchmark covers this
end-to-end task (sheet → axis grid → columns → beams → 3D frame).

**Who created the dataset and on behalf of which entity?**
Withheld for double-blind review.

**Funding sources?**
Withheld for double-blind review.

---

## 2. Composition

**What do the instances represent?**
Each instance is one *building*: a set of structural plan sheets across
1–5 floors, together with hand-verified ground-truth annotations of:
axis grid (horizontal/vertical axis labels and positions), columns
(coordinates, section labels), and beams (endpoints, span topology,
section labels).

**Total instances:** **20 buildings, approximately 300 scanned structural
blueprint sheets.** The corpus consists primarily of beam and column plan
sheets, with associated section and foundation sheets per building
(~15 sheets per building on average).

**Difficulty distribution:** easy / medium / hard categories assigned per
building based on number of floors, axis-grid complexity, and cross-sheet
aggregation requirements. The exact per-building breakdown (floors, beam
entities, columns, difficulty) is reported in Table 1 of the paper.

**Are there labels?** Yes — annotation schema documented in
`data/gt/README.md` and `cvn.gt.skeleton.v1`. All 20 buildings have
complete ground-truth annotations internally. **Released:** the
per-entity ground truth for the one sample project only (`data/gt/`).
**Withheld:** per-entity ground truth for the other 19 buildings (see
§ 6 for the rationale; their inventory aggregates remain readable from
`data/metrics/`).

**Are there recommended splits?** No — the dataset is used purely for
end-to-end evaluation, not for training. We report per-instance metrics
and a macro-average across the 20 buildings.

**Are there any errors or noise?**
The ground truth is "silver standard": derived from a manually verified
StructAgent run, then cross-checked against the original drawings by the
authors. Per-instance annotation effort: 2–6 hours per building.

**Does the dataset contain confidential or sensitive information?**
The drawings do not contain personal identifying information. Some
drawings carry design-institute stamps, project codes, or engineer
signatures; these are masked in the released sample project. The
underlying source drawings of the 19 non-sample buildings are not
redistributed.

---

## 3. Collection

**How was the data acquired?**
Mixed sources, separated by redistribution constraint:

- **Releasable subset (research-only license):** drawings from publicly
  available teaching materials or open engineering references whose
  redistribution under research-only terms is unambiguous. The single
  released sample project (`data/samples/`) is drawn from this subset.
- **Non-redistributable subset:** drawings whose redistribution rights are
  unclear or restricted. Used internally for evaluation; **ground truth and
  per-instance metrics are released** (these are derived statistics, not the
  source drawings); the **source drawings themselves are not released**.

Of the 20 buildings, the releasable subset is small (one sample project,
approximately 10 sheets); the remaining 19 buildings fall under the
non-redistributable subset. This release strategy is conservative by design
and is grounded in the sensitivity considerations described above and in
the paper § 5.1.

**Selection.** The 20-building evaluation set was assembled to maximize
difficulty diversity (easy / medium / hard) while keeping manual annotation
tractable. Earlier-stage candidates rejected during quality screening
(e.g., projects flagged for unresolvable cross-sheet inconsistencies, or
projects whose audit-gate signals were ambiguous) are documented internally
and discussed in the paper § 5.1.

**Over what timeframe?**
2024–2026.

**Were ethical review processes consulted?**
No human subjects; no IRB review required. The drawings are engineering
artifacts. No personal identifying information is present.

---

## 4. Preprocessing

**Was any preprocessing applied to the raw data?**
For evaluation: drawings are converted to PNG at native resolution and fed
to the pipeline. Internal stages (Stage 0.5 OCR, Stage 1 layout analysis,
Stage 1.5 tiling) are described in the paper § 4 and exposed in
`code/agent/agent_interface.py`.

For the released sample project: drawings are downsampled to ≤ 200 dpi and
any design-institute stamps, project codes, and engineer signatures are
masked. Original EXIF metadata is stripped. Filenames are normalized to
remove any project-specific codes.

**Is the "raw" data saved in addition to the preprocessed data?**
Yes, internally. Not released.

---

## 5. Uses

**Has the dataset been used for any tasks already?**
Only for the present paper (system evaluation).

**What other tasks could the dataset be used for?**
Layout analysis, structural element detection, multimodal document
understanding, agent benchmarking. Not suitable for training large models
(too small).

**Anything that should not be done with it?**
- Not for commercial use (research-only license).
- Not as ground truth for safety-critical engineering decisions.
- Not for retraining drawing-recognition systems intended for unsupervised
  structural FEM generation in production.
- The released sample project must not be reposted in a way that strips
  the redaction or the research-only license terms.

---

## 6. Distribution

**To whom will the dataset be distributed?**
- **Now (review period), via the anonymous repository:**
  - **One sample project**, complete bundle: redacted source sheets
    (`data/samples/`, ~10 PNGs), per-entity ground-truth JSON
    (`data/gt/<sample_id>.gt.json`), and per-instance metrics for every
    experiment cell evaluated on this project (`data/metrics/<sample_id>__*.json`).
  - **Other 19 buildings:** per-instance metrics JSON only
    (`data/metrics/<other_id>__*.json`). Each metrics file includes
    inventory aggregates for both prediction and ground truth.
  - Evaluation code (`code/eval/`), agent interface stub (`code/agent/`),
    `DATASHEET`, `RESPONSIBLE_NLP_CHECKLIST_NOTES`, `LICENSE`.
- **After acceptance:** Same materials under the authors' named repository.
- **On request, case-by-case, to qualified researchers:** Additional
  buildings (drawings and/or per-entity GT), subject to the redistribution
  constraints of each source. The full corpus will not be released publicly.

**Why is even the ground truth only partially released?**
Per-entity ground truth (axis grid, column positions, beam topology,
section labels) encodes the structural skeleton of a building in a form
sufficient to draw a structural plan resembling the original. Treating it
as fully releasable while withholding the source drawings would be
internally inconsistent with the mixed-source redistribution constraints
described in § 3. We therefore release per-entity ground truth for one
sample project only, and use the per-instance metrics JSON (with inventory
aggregates) as the verification artifact for the other 19 buildings.

**Why is this still sufficient for reproducibility?**
Reviewers can verify the reported metric values in three ways:

1. **End-to-end on the sample project.** Run our agent (or your own) on
   the released sample drawings, then evaluate against the released GT
   using our code. Cross-check the resulting metric against the released
   metrics JSON for that project.
2. **Cross-building inventory consistency.** Inspect `inventory.pred` vs
   `inventory.gt` in every metrics JSON; these aggregate counts (floors,
   axes, columns, beams) are released for all 20 buildings.
3. **Macro-average reconstruction.** Run `code/eval/aggregate.py` on the
   released metrics to reproduce Tables 3 and 4.

Comparable partial-release practice has been accepted at recent ACL
venues (e.g., Storks et al., ACL 2023 long, which releases analysis
code and a sample data template while withholding IRB-protected subject
data).

**License:**
- Code: CC BY-NC 4.0
- Data: CC BY-NC-ND 4.0

---

## 7. Maintenance

**Who maintains it?**
The authors (identity withheld for review).

**How can the dataset be updated, and by whom?**
Bug reports and corrections via the repository issue tracker after
acceptance.

**Will older versions be supported?**
Yes — version-tagged releases on the named repository post-acceptance.

---

*Last updated: 2026-05.*
