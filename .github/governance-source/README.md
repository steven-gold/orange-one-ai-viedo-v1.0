# Governance Full-Source CI Materialization

This directory is **non-normative CI source materialization**, not a second Current Specification authority.

Authority remains resolved only through `governance/specifications/REGISTRY.yaml` and `governance/specifications/current/`.

The source snapshot under `active/source/` is the exact 75-file verified-source lineage set. It exists for reproducible source-identity verification, Current execution-profile lineage resolution, Mother-governance read continuity, and full-line high-pressure regression. Its historical version prose MUST NOT override the active governance UID or display version resolved from the Current Registry.

Post-materialization state:
- `active/source/` is the only retained full-source lineage snapshot.
- Bootstrap transport chunks, bootstrap manifests, one-time materializer code, materializer trigger, and materializer workflow are not Current inputs.
- Historical bootstrap and execution evidence belongs in Git history / GitHub Actions evidence unless a Current owner explicitly retains it.

Current verified-source identity:
- file count: `75`
- checksum entries: `74`
- checksum manifest SHA256: `30d660da649521f33503ffe59c61e4257d36f057601cd1e71326194f4934b123`
- deterministic source-content bundle SHA256: `655519ff9e456739903a04bd049ade37b0a51148966f196eebb87770544a642b`
- deterministic source ZIP SHA256: `8d60815f6d06c6f46d93a17cf82b606011670dde5b72691dd482e27c91d97871`
- semantic authority content hash: `c213b2ec8d2e1f82627a3ed50fa715e440515d1b3ed2e66facc8f5f36095e6c8`

Rules:
- The retained source-content set must contain exactly 75 files.
- `CHECKSUMS.sha256` must contain exactly 74 source entries and the exact path set; the checksum file itself is the 75th file.
- Every listed source file must match its package checksum.
- Source-identity pins above are lineage-integrity evidence; they are not Current Governance version selectors.
- Round-1 Full-Line testing must execute the complete registered mandatory regression matrix and the 11-stage lifecycle definition coverage.
- Normal lifecycle Stage execution must use the Stage selector and load only that Stage's registered files plus registered shared dependencies; it must not semantically load all 75 files by default.
- This directory must never be used as a competing Current Specification locator by product/construction consumers.
- A missing file, hash mismatch, path-set mismatch, missing suite, suite timeout, denominator mismatch, skipped mandatory suite, mutation, or residual runtime artifact is a hard failure.
- High-pressure SYSTEM Round-1 is distinct from practical/product Stage testing. A SYSTEM PASS does not create product Stage completion credit.
