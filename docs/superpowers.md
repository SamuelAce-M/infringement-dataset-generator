# Superpowers Development Control

## Scope

This project builds training image libraries only. It does not train models, provide training framework adapters, split train/validation/test sets, or run training jobs.

## Current Objective

Deliver a usable external-design-patent image-library generator:

- Import registry images from local or URL manifests.
- Import negative samples from local or URL manifests.
- Generate positive and mid-band samples from registry images.
- Write traceable metadata.
- Validate generated image-library batches.
- Probe online patent/design sources without polluting production data.

## Gates

### Gate 1: Requirements

- [x] Scope excludes model training.
- [x] Similarity bands are defined: positive `>=0.55`, mid `>=0.40 <0.55`, negative `<0.40`.
- [x] Placeholder data is explicit test/demo-only.

### Gate 2: Application Surface

- [x] `prepare-manifests`
- [x] `generate`
- [x] `validate`
- [x] `source-spike`
- [x] `wipo-inspect`
- [x] `wipo-export` experimental blocker command

### Gate 3: Dataset Integrity

- [x] Metadata has source, transformations, similarity score, and band.
- [x] Validator checks files, image shape, JSON transformations, thresholds, and duplicates.
- [x] Repo `datasets/` batch regenerated with new metadata format and passes validation.

### Gate 4: Online Sources

- [x] URL manifest import works.
- [x] WIPO source inspection works with external network.
- [x] CNIPA legacy endpoint is recorded as unavailable.
- [x] WIPO query-state generation and image URL extraction are explicitly deferred.

Deferral reason: WIPO DesignDB uses compressed frontend `qz` state, direct `q=` queries return `INVALID_INPUT`, and WIPO UI text warns against automatic bulk retrieval. The application therefore supports URL manifests and explicit source inspection, but does not implement uncontrolled WIPO crawling.

## Current Completion Status

- [x] Current MVP requirements are complete.
- [x] Checked-in `datasets/` batch passes validation.
- [x] Application tests pass.
- [x] Online source automation is safely bounded by source-spike, wipo-inspect, and wipo-export blocker reports.
- [x] Training is excluded from scope and documented as out of scope.

## Required Verification

Run before considering a task complete:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python main.py validate --root datasets
```

Both commands must pass before a dataset-integrity task is considered complete.
