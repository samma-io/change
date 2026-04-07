import sys
import socket


def collect(target: str, config: dict) -> dict:
    """
    Returns: {"80": "open", "443": "open", "22": "closed", ...}
    On error connecting to a port: mark as "error".
    On total failure: return {}
    """
    try:
        scan_ports = config.get('scan_ports', [80, 443, 22, 8080, 8443])
        timeout = int(config.get('timeout', 3))

        result = {}
        for port in scan_ports:
            port = int(port)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            try:
                res = sock.connect_ex((target, port))
                result[str(port)] = 'open' if res == 0 else 'closed'
            except Exception as e:
                print(f"ports collector error for {target}:{port}: {e}", file=sys.stderr)
                result[str(port)] = 'error'
            finally:
                sock.close()

        return result

    except Exception as e:
        print(f"ports collector total failure for {target}: {e}", file=sys.stderr)
        return {}
