import sys
import socket


def collect(target: str, config: dict) -> dict:
    """
    Returns: {"banner": "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3", "software": "OpenSSH_8.9p1"}
    On error/no SSH: return {"error": str(e)}
    """
    try:
        port = int(config.get('ssh_port', 22))
        timeout = int(config.get('timeout', 5))

        with socket.create_connection((target, port), timeout=timeout) as sock:
            raw = sock.recv(256).decode('utf-8', errors='replace').strip()
            banner = raw
            software = None
            # SSH banner format: SSH-<protoversion>-<softwareversion> [comment]
            # e.g. "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3"
            if raw.startswith('SSH-'):
                parts = raw.split('-', 2)
                if len(parts) >= 3:
                    software = parts[2].split()[0]

            return {'banner': banner, 'software': software}

    except Exception as e:
        print(f"ssh_banner collector error for {target}: {e}", file=sys.stderr)
        return {'error': str(e)}
