import sys
import http.client


def collect(target: str, config: dict) -> dict:
    """
    Returns: plain dict of ALL response headers (key→value, lowercase keys).
    Also includes "_status_code": int.
    On error: return {}
    """
    try:
        https_val = config.get('https', True)
        if isinstance(https_val, str):
            https = https_val.lower() not in ('false', '0', 'no')
        else:
            https = bool(https_val)

        default_port = 443 if https else 80
        port = int(config.get('http_port', default_port))
        timeout = int(config.get('timeout', 5))

        if https:
            conn = http.client.HTTPSConnection(target, port, timeout=timeout)
        else:
            conn = http.client.HTTPConnection(target, port, timeout=timeout)

        conn.request('HEAD', '/')
        resp = conn.getresponse()
        status_code = resp.status
        headers = {k.lower(): v for k, v in resp.getheaders()}
        conn.close()

        headers['_status_code'] = status_code
        return headers

    except Exception as e:
        print(f"http_headers collector error for {target}: {e}", file=sys.stderr)
        return {}
