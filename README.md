# Infringement Dataset Generator

Generate and validate image datasets for infringement detection experiments.

This project builds training image libraries only. It does not train models, split train/validation/test sets, provide PyTorch Dataset classes, or run training jobs.

## Status

Current MVP is complete:

- Local and URL manifest import
- Positive, mid-band, and negative image-library generation
- Traceable metadata
- Dataset validation
- Source probing for online patent/design databases
- WIPO inspection and explicit blocked export reporting

## Current MVP

The current flow is local-manifest first:

```bash
python main.py prepare-manifests \
  --registry-dir datasets/registry/外观设计专利 \
  --negative-dir datasets/training/外观设计专利/negative \
  --registry-output /tmp/registry_manifest.csv \
  --negative-output /tmp/negative_manifest.csv

python main.py generate \
  --type 外观设计专利 \
  --registry file /tmp/registry_manifest.csv \
  --negative-source /tmp/negative_manifest.csv \
  --registry-count 5 \
  --positive 20 \
  --negative 20 \
  --output /tmp/design_patent_dataset

python main.py validate --root /tmp/design_patent_dataset
```

`--allow-placeholder` is for tests and demos only. Production runs should use local manifests or a validated online data source.

## Online Source Spike

Probe candidate online patent/design sources:

```bash
python main.py source-spike --output /tmp/source_spike.json --timeout 10
```

Inspect WIPO DesignDB frontend wiring for adapter development:

```bash
python main.py wipo-inspect --output /tmp/wipo_inspect.json --timeout 10
```

The WIPO UI currently uses compressed frontend search state and warns against automatic bulk retrieval. Treat any WIPO adapter as an explicit, low-volume manifest export tool, not an uncontrolled crawler.

Experimental WIPO export command:

```bash
python main.py wipo-export \
  --keyword cup \
  --limit 5 \
  --output /tmp/wipo_registry_manifest.csv \
  --report /tmp/wipo_export.json \
  --acknowledge-limits
```

This command currently fails visible after inspection because WIPO uses compressed `qz` search state and image URL extraction is not implemented yet. It writes a header-only manifest and a JSON blocker report.

Current production import supports URL manifests. The manifest format is the same as local import, but the image field may be `http://` or `https://`:

```csv
registry_id,image_path
REG001,https://example.com/design-image.png
```

Negative URL manifests require an explicit score:

```csv
sample_id,image_path,registry_id,similarity_score
NEG001,https://example.com/other-design.png,REG001,0.20
```

The app will normalize downloaded images to 512x512 RGB PNG and write the dataset through the same metadata and validation path.
