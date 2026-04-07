# change

Stateful change scanners for the [samma-io](https://github.com/samma-io) security platform. Sibling project to [detect](https://github.com/samma-io/detect).

While `detect` covers point-in-time network signals, `change` monitors targets **over time** — storing a baseline on first run and emitting one finding per detected change on every subsequent run. This catches supply-chain attacks, infrastructure drift, certificate swaps, DNS hijacks, and page-level compromise.

---

## Scanners

| Scanner | Layer | What it monitors |
|---|---|---|
| [web-change-scanner](web-change-scanner/) | Application | Rendered page content — scripts, links, forms, iframes, headers, cookies, resources |
| [network-change-scanner](network-change-scanner/) | Network | TLS certs/ciphers, DNS records, HTTP headers, ports, routes, SSH banners, redirects, WHOIS |

---

## Architecture

Each scanner follows the same pattern as `detect`:

- **Containerized** — runs as a Docker container or Kubernetes CronJob
- **Short-lived** — starts, scans, emits findings, exits
- **Stateful** — stores a baseline snapshot between runs; diffs on each subsequent run
- **One finding per change** — each detected mutation is a separate JSON event
- **NATS + NDJSON output** — findings published to NATS and/or written to `/out/*.json`

Baseline storage is automatic: filesystem by default, NATS JetStream KV when `NATS_ENABLED=true`.

---

## Quick Start

```bash
# Web change scanner — detects page-level mutations
cd web-change-scanner
TARGET=https://example.com WRITE_TO_FILE=True docker compose run --rm web-change-scanner

# Network change scanner — detects low-level network mutations
cd network-change-scanner
TARGET=example.com WRITE_TO_FILE=True docker compose run --rm network-change-scanner

# Run again to detect changes (first run establishes baseline)
```

---

## Output Format

### Web scanner finding

```json
{
  "url": "https://example.com",
  "domain": "example.com",
  "category": "scripts",
  "change_type": "added",
  "old_value": null,
  "new_value": "https://cdn.evil.com/tracker.js",
  "type": "WebChange",
  "samma-io": { "scanner": "web-change-scanner", "id": "1234", "tags": ["scanner"], "json": {} }
}
```

### Network scanner finding

```json
{
  "target": "example.com",
  "category": "tls",
  "field": "cipher",
  "change_type": "modified",
  "old_value": "TLS_CHACHA20_POLY1305_SHA256",
  "new_value": "TLS_AES_256_GCM_SHA384",
  "type": "NetworkChange",
  "samma-io": { "scanner": "network-change-scanner", "id": "1234", "tags": ["scanner"], "json": {} }
}
```

On first run, a baseline finding is emitted (`type: "WebChangeBaseline"` or `"NetworkChangeBaseline"`).

---

## Common Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `TARGET` | required | URL or hostname to scan |
| `WRITE_TO_FILE` | `False` | Write findings to `/out/<PARSER>.json` |
| `NATS_ENABLED` | `False` | Enable NATS publishing + KV baseline storage |
| `NATS_URL` | `nats://localhost:4222` | NATS server address |
| `NATS_SUBJECT` | `samma-io.scan` | NATS publish subject |
| `SAMMA_IO_ID` | `1234` | Deployment ID (tag your instances) |
| `SAMMA_IO_TAGS` | `scanner` | Comma-separated tags |
