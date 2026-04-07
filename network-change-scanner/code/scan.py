import os
import sys
from urllib.parse import urlparse

import sammaParser
import storage
import differ
import collectors.tls
import collectors.dns_records
import collectors.http_headers
import collectors.ports
import collectors.traceroute
import collectors.ssh_banner
import collectors.redirects
import collectors.whois_info

TARGET = os.getenv('TARGET')
if not TARGET:
    print('TARGET env var is required', file=sys.stderr)
    sys.exit(1)

parsed = urlparse(TARGET if '://' in TARGET else 'http://' + TARGET)
hostname = parsed.hostname or TARGET

COLLECTOR_MAP = {
    'tls': collectors.tls.collect,
    'dns': collectors.dns_records.collect,
    'http_headers': collectors.http_headers.collect,
    'ports': collectors.ports.collect,
    'traceroute': collectors.traceroute.collect,
    'ssh_banner': collectors.ssh_banner.collect,
    'redirects': collectors.redirects.collect,
    'whois': collectors.whois_info.collect,
}

try:
    CATEGORIES_ENV = os.getenv('CATEGORIES', 'tls,dns,http_headers,ports')
    if CATEGORIES_ENV.strip().lower() == 'all':
        CATEGORIES = ['tls', 'dns', 'http_headers', 'ports', 'traceroute', 'ssh_banner', 'redirects', 'whois']
    else:
        CATEGORIES = [c.strip() for c in CATEGORIES_ENV.split(',') if c.strip()]

    config = {
        'tls_port': int(os.getenv('TLS_PORT', '443')),
        'http_port': int(os.getenv('HTTP_PORT', '443')),
        'https': os.getenv('HTTPS', 'True').lower() not in ('false', '0', 'no'),
        'ssh_port': int(os.getenv('SSH_PORT', '22')),
        'scan_ports': [int(p) for p in os.getenv('SCAN_PORTS', '80,443,22,8080,8443').split(',')],
        'dns_record_types': [r.strip() for r in os.getenv('DNS_RECORD_TYPES', 'A,AAAA,MX,TXT,NS').split(',')],
        'max_hops': int(os.getenv('MAX_HOPS', '30')),
        'max_redirects': int(os.getenv('MAX_REDIRECTS', '10')),
        'timeout': int(os.getenv('TIMEOUT', '5')),
    }

    target_key = hostname

    baseline = storage.load(target_key)

    snapshot = {}
    for category in CATEGORIES:
        collector_fn = COLLECTOR_MAP.get(category)
        if collector_fn:
            try:
                snapshot[category] = collector_fn(hostname, config)
            except Exception as e:
                print(f'[scan] collector {category} failed: {e}', file=sys.stderr)
                snapshot[category] = {}

    if not baseline:
        try:
            storage.save(target_key, snapshot)
        except Exception as e:
            sammaParser.logger({
                "target": hostname,
                "category": "error",
                "change_type": "baseline_save_failed",
                "old_value": None,
                "new_value": str(e),
                "type": "NetworkChange",
            })
        sammaParser.logger({
            "target": hostname,
            "type": "NetworkChangeBaseline",
            "categories_collected": list(snapshot.keys()),
        })
        sammaParser.endThis()
    else:
        findings = differ.compare(baseline, snapshot)
        for finding in findings:
            sammaParser.logger({"target": hostname, "type": "NetworkChange", **finding})
        try:
            storage.save(target_key, snapshot)
        except Exception as e:
            sammaParser.logger({
                "target": hostname,
                "category": "error",
                "change_type": "baseline_save_failed",
                "old_value": None,
                "new_value": str(e),
                "type": "NetworkChange",
            })
        sammaParser.endThis()

except Exception as e:
    try:
        sammaParser.logger({
            "target": hostname,
            "category": "error",
            "change_type": "scan_failed",
            "old_value": None,
            "new_value": str(e),
            "type": "NetworkChange",
        })
        sammaParser.endThis()
    except Exception:
        pass
    sys.exit(1)
