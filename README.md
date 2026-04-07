# change

Stateful web change scanners for the [samma-io](https://github.com/samma-io) security platform. Sibling project to [detect](https://github.com/samma-io/detect).

While `detect` covers network-layer signals (ports, TLS, DNS, HTTP headers), `change` monitors **rendered web page content over time** — catching injected scripts, altered links, form hijacking, and other mutations that indicate compromise or supply-chain attacks.

---

## Scanners

| Scanner | What it monitors |
|---|---|
| [web-change-scanner](web-change-scanner/) | Full rendered page snapshot — scripts, links, forms, iframes, headers, cookies, resources |

---

## Architecture

Each scanner follows the same pattern as `detect`:

- **Containerized** — runs as a Docker container or Kubernetes CronJob
- **Short-lived** — starts, scans, emits findings, exits
- **Stateful** — stores a baseline snapshot between runs; diffs on each subsequent run
- **One finding per change** — each detected mutation is a separate JSON event
- **NATS + NDJSON output** — findings published to NATS and/or written to `/out/*.json`

---

## Quick Start

```bash
# Run against a target (first run establishes baseline)
cd web-change-scanner
TARGET=https://example.com WRITE_TO_FILE=True docker compose run --rm web-change-scanner

# Run again to detect changes
TARGET=https://example.com WRITE_TO_FILE=True docker compose run --rm web-change-scanner
```

---

## Output Format

Each finding is a JSON object:

```json
{
  "url": "https://example.com",
  "domain": "example.com",
  "category": "scripts",
  "change_type": "added",
  "old_value": null,
  "new_value": "https://cdn.evil.com/tracker.js",
  "type": "WebChange",
  "samma-io": {
    "scanner": "web-change-scanner",
    "id": "1234",
    "tags": ["scanner"],
    "json": {}
  }
}
```

On first run, a baseline finding is emitted:

```json
{
  "url": "https://example.com",
  "domain": "example.com",
  "type": "WebChangeBaseline",
  "categories_captured": ["scripts", "links", "forms", "iframes", "headers", "cookies", "resources"]
}
```

---

## Common Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `TARGET` | required | Full URL to scan |
| `WRITE_TO_FILE` | `False` | Write findings to `/out/<PARSER>.json` |
| `NATS_ENABLED` | `False` | Enable NATS publishing + KV baseline storage |
| `NATS_URL` | `nats://localhost:4222` | NATS server address |
| `NATS_SUBJECT` | `samma-io.scan` | NATS publish subject |
| `SAMMA_IO_ID` | `1234` | Deployment ID (tag your instances) |
| `SAMMA_IO_TAGS` | `scanner` | Comma-separated tags |
