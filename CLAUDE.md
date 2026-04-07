# CLAUDE.md

This is the `change` project — stateful web change scanners for the samma-io security platform.

## Project Structure

```
change/
├── web-change-scanner/     # Detects changes in rendered web page content
│   ├── code/               # Node.js source (ES modules)
│   │   ├── scan.js         # Entrypoint
│   │   ├── extractor.js    # Playwright extraction
│   │   ├── differ.js       # Snapshot diffing
│   │   ├── storage.js      # Baseline persistence
│   │   └── sammaParser.js  # Output (NATS + NDJSON)
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   └── manifest/           # Kubernetes Job + CronJob
└── docs/superpowers/specs/ # Design documents
```

## Relationship to `detect`

The sibling project at `../detect` contains 8 Python network scanners (port, TLS, DNS, etc.). This project follows the **same patterns** but:

- Uses **Node.js** (not Python) because Playwright fits the JS ecosystem
- Is **stateful** — stores a baseline snapshot between runs
- Has a `sammaParser.js` that mirrors `sammaParser.py` from detect

Always follow the detect conventions when adding new scanners here.

## Scanner Pattern

Every scanner must:
1. Accept `TARGET` env var (required — full URL)
2. Call `sammaParser.logger(finding)` once per finding
3. Call `sammaParser.endThis()` at the end of every run (writes `/out/die`)
4. Handle all errors non-fatally — scanner must always reach `endThis()`
5. Run as a short-lived container (CronJob pattern, not a daemon)

## Key Conventions

**NATS_ENABLED flag:** The string `'False'` means disabled; anything else means enabled. This matches the Python scanners in detect. Do NOT change this convention.

**Baseline storage:** `storage.js` abstracts filesystem vs NATS KV. Always go through `storage.load(domain)` / `storage.save(domain, snapshot)` — never write baseline files directly.

**Header ignore list:** Ephemeral headers (`date`, `age`, `cf-ray`, etc.) are filtered in `differ.js`. Add to `DEFAULT_HEADER_IGNORE` if new noisy headers are discovered.

**One finding per change:** Each call to `logger()` is one security event. Keep findings granular.

## Running Locally

```bash
cd web-change-scanner

# Build
docker compose build

# First run (establishes baseline)
TARGET=https://example.com WRITE_TO_FILE=True docker compose run --rm web-change-scanner

# Subsequent runs (emits change findings)
TARGET=https://example.com WRITE_TO_FILE=True docker compose run --rm web-change-scanner
```

## Adding a New Scanner

1. Create `<scanner-name>/` directory mirroring `web-change-scanner/` structure
2. Implement `scan.js` (entrypoint), plus any modules needed
3. Copy and adapt `sammaParser.js` (or import from a shared location if one is created)
4. Add `Dockerfile`, `docker-compose.yaml`, `manifest/job.yaml`, `manifest/cron.yaml`
5. Document in `<scanner-name>/README.md`

## Design Docs

Specs live in `docs/superpowers/specs/`. Read them for rationale behind design decisions.
