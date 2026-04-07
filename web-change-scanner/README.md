# web-change-scanner

Renders a target URL with a headless browser, stores a categorized snapshot as a baseline, and on each subsequent run diffs the snapshot against the stored baseline — emitting one finding per detected change.

Catches: injected scripts, altered links, form action changes, new iframes, cookie flag downgrades, CSP/security header mutations, and new external resources.

---

## How It Works

```
First run:   render page → extract snapshot → save as baseline → emit WebChangeBaseline
Later runs:  render page → extract snapshot → diff vs baseline → emit one finding per change → update baseline
```

The scanner is stateless between runs — all state lives in the baseline file (filesystem or NATS KV).

---

## Change Detection Categories

| Category | What's tracked | Change types |
|---|---|---|
| `scripts` | External script URLs + SHA-256 hashes of inline scripts | added, removed, modified |
| `links` | All `<a href>` values | added, removed |
| `forms` | Form `action`, `method`, `enctype` | added, removed, modified |
| `iframes` | `<iframe src>` values | added, removed |
| `headers` | HTTP response headers (CSP, HSTS, X-Frame-Options, etc.) | added, removed, modified |
| `cookies` | Cookie names + HttpOnly/Secure/SameSite flags | added, removed, modified |
| `resources` | External CSS, images, fonts loaded by the page | added, removed |

Ephemeral headers (`date`, `age`, `cf-ray`, `x-request-id`, etc.) are ignored by default to prevent noise.

---

## Running Locally

```bash
# First run — establishes baseline
TARGET=https://example.com WRITE_TO_FILE=True docker compose run --rm web-change-scanner

# Subsequent runs — emits findings for any changes
TARGET=https://example.com WRITE_TO_FILE=True docker compose run --rm web-change-scanner

# Results written to ./out/web-change-scanner.json
# Baseline stored at ./out/web-change-scanner.example.com.baseline.json
```

---

## Environment Variables

### Common (matches all detect scanners)

| Variable | Default | Purpose |
|---|---|---|
| `TARGET` | **required** | Full URL to scan (e.g. `https://example.com/login`) |
| `WRITE_TO_FILE` | `False` | Write findings to `/out/<PARSER>.json` |
| `PARSER` | `web-change-scanner` | Output filename prefix |
| `SAMMA_IO_SCANNER` | `web-change-scanner` | Scanner label in finding metadata |
| `SAMMA_IO_ID` | `1234` | Deployment ID |
| `SAMMA_IO_TAGS` | `scanner` | Comma-separated tags |
| `NATS_ENABLED` | `False` | Enable NATS publishing + KV baseline |
| `NATS_URL` | `nats://localhost:4222` | NATS server |
| `NATS_SUBJECT` | `samma-io.scan` | NATS publish subject |

### Scanner-specific

| Variable | Default | Purpose |
|---|---|---|
| `PLAYWRIGHT_TIMEOUT` | `30000` | Page load timeout (ms) |
| `PLAYWRIGHT_WAIT` | `networkidle` | Wait strategy: `networkidle` or `load` |
| `HEADER_IGNORE` | _(empty)_ | Extra comma-separated headers to ignore in diffs |

---

## Baseline Storage

### Filesystem (default)

Baseline saved to `/out/web-change-scanner.<domain>.baseline.json`.

Mount a persistent volume to retain the baseline between CronJob runs:

```yaml
volumes:
  - /data/change-scanner:/out
```

### NATS JetStream KV (`NATS_ENABLED=true`)

Baseline stored in NATS KV bucket `web-change-scanner`, keyed by domain. Recommended for production — no persistent volume needed, and multiple scanner instances share storage safely.

---

## Multiple Targets

Run one container per target. Each writes its baseline under its own domain key, so they never collide:

```bash
TARGET=https://example.com docker compose run --rm web-change-scanner
TARGET=https://app.example.com docker compose run --rm web-change-scanner
TARGET=https://admin.example.com docker compose run --rm web-change-scanner
```

---

## Kubernetes Deployment

```bash
# One-off job
kubectl apply -f manifest/job.yaml

# CronJob (hourly, concurrencyPolicy: Forbid)
kubectl apply -f manifest/cron.yaml
```

Edit `manifest/cron.yaml` to set `TARGET` and configure NATS before deploying.

---

## File Structure

```
web-change-scanner/
├── code/
│   ├── scan.js           # Entrypoint — orchestrates full scan lifecycle
│   ├── extractor.js      # Playwright extraction (7 categories)
│   ├── differ.js         # Snapshot comparison → findings[]
│   ├── storage.js        # Baseline read/write (filesystem or NATS KV)
│   ├── sammaParser.js    # Output: NATS publish + NDJSON file write
│   └── package.json
├── Dockerfile
├── docker-compose.yaml
└── manifest/
    ├── job.yaml          # Kubernetes one-off Job
    └── cron.yaml         # Kubernetes CronJob (hourly)
```
