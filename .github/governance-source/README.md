# Governance Full-Source CI Materialization

This directory is **non-normative CI source materialization**, not a second Current Specification authority.

Authority remains resolved only through `governance/specifications/REGISTRY.yaml` and `governance/specifications/current/`.

The source snapshot materialized here is the exact 75-file source-content set extracted from the Current Manifest lineage package. Its purpose is reproducible GitHub integrity and full-line high-pressure regression testing.

Rules:
- The complete source-content set must reconstruct to exactly 75 files.
- Every reconstructed file must match the package `CHECKSUMS.sha256` entry.
- Round-1 full-line system testing reads/validates the whole source set and executes every registered mandatory regression suite.
- Normal lifecycle Stage execution must use the Stage selector and load only that Stage's registered files plus registered shared dependencies; it must not semantically load all 75 files by default.
- This directory must never be used as the active governance locator by product/construction consumers.
- A missing chunk, hash mismatch, missing suite, suite timeout, denominator mismatch, skipped suite, or residual test artifact is a hard failure.
