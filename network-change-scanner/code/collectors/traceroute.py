import sys
import re
import subprocess


def collect(target: str, config: dict) -> dict:
    """
    Returns: {"hops": [{"hop": 1, "ip": "x.x.x.x", "rtt_ms": 1.2}, ...]}
    IPs that don't respond: ip = None, rtt_ms = None.
    On error: return {}
    """
    try:
        max_hops = int(config.get('max_hops', 30))
        timeout = int(config.get('timeout', 2))

        cmd = ['traceroute', '-n', '-q', '1', '-w', str(timeout), '-m', str(max_hops), target]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=max_hops * timeout + 10)

        hop_pattern = re.compile(r'^\s*(\d+)\s+(\S+)\s+(\d+\.\d+)\s+ms')
        star_pattern = re.compile(r'^\s*(\d+)\s+\*')

        hops = []
        for line in result.stdout.splitlines():
            hop_match = hop_pattern.match(line)
            star_match = star_pattern.match(line)

            if hop_match:
                hops.append({
                    'hop': int(hop_match.group(1)),
                    'ip': hop_match.group(2),
                    'rtt_ms': float(hop_match.group(3)),
                })
            elif star_match:
                hops.append({
                    'hop': int(star_match.group(1)),
                    'ip': None,
                    'rtt_ms': None,
                })

        return {'hops': hops}

    except Exception as e:
        print(f"traceroute collector error for {target}: {e}", file=sys.stderr)
        return {}
