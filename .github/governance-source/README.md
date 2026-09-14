# Governance Full-Source CI Materialization

This directory is **non-normative CI source materialization**, not a second Current Specification authority.

Authority remains resolved only through `governance/specifications/REGISTRY.yaml` and `governance/specifications/current/`.

The source snapshot under `active/source/` is the exact 75-file source-content set extracted from the verified governance lineage package. It exists only for reproducible GitHub integrity verification and full-line high-pressure system regression.

Post-materialization state:
- `active/source/` is the only retained full-source snapshot.
- Bootstrap transport chunks, bootstrap manifests, one-time materializer code, materializer trigger, and materializer workflow are removed after successful 75/75 materialization and identity verification.
- Historical bootstrap evidence remains only in Git history / GitHub Actions evidence and is not a live governance input.

Rules:
- The retained source-content set must contain exactly 75 files.
- `CHECKSUMS.sha256` must contain exactly 74 source entries and the exact path set; the checksum file itself is the 75th file.
- Every listed source file must match its package checksum.
- Deterministic rebundling must equal SHA256 `b5bf1af1817e41832e53aeb6e4b78f7fa0c24ac41204fe6de2a69eb663ceb625`.
- Round-1 full-line system testing must execute the complete registered mandatory regression matrix and the 11-stage lifecycle definition coverage.
- Normal lifecycle Stage execution must use the Stage selector and load only that Stage's registered files plus registered shared dependencies; it must not semantically load all 75 files by default.
- This directory must never be used as the active governance locator by product/construction consumers.
- A missing file, hash mismatch, path-set mismatch, missing suite, suite timeout, denominator mismatch, skipped suite, mutation, or residual test artifact is a hard failure.
- High-pressure SYSTEM Round-1 is distinct from practical/product Stage testing. A SYSTEM PASS does not create Stage-02 execution evidence.
