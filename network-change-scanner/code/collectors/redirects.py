import sys
import urllib.request
import urllib.error


def collect(target: str, config: dict) -> dict:
    """
    Returns: {"hops": [
      {"hop": 1, "url": "http://example.com", "status_code": 301, "redirect_to": "https://...", "final": False},
      {"hop": 2, "url": "https://example.com", "status_code": 200, "redirect_to": None, "final": True}
    ]}
    On error: return {}
    """
    try:
        timeout = int(config.get('timeout', 5))
        max_redirects = int(config.get('max_redirects', 10))

        # Ensure URL has scheme
        current_url = target if target.startswith('http') else 'http://' + target

        # Opener that does NOT auto-follow redirects
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirectHandler())

        hops = []
        hop = 1
        while hop <= max_redirects:
            response = None
            done = False
            try:
                response = opener.open(current_url, timeout=timeout)
                hops.append({
                    'hop': hop,
                    'url': current_url,
                    'status_code': response.status,
                    'redirect_to': None,
                    'final': True,
                })
                done = True
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308):
                    location = e.headers.get('Location', '')
                    hops.append({
                        'hop': hop,
                        'url': current_url,
                        'status_code': e.code,
                        'redirect_to': location,
                        'final': False,
                    })
                    current_url = location
                    hop += 1
                else:
                    hops.append({
                        'hop': hop,
                        'url': current_url,
                        'status_code': e.code,
                        'redirect_to': None,
                        'final': True,
                    })
                    done = True
            except Exception as e:
                print(f"redirects collector error for {target} at hop {hop}: {e}", file=sys.stderr)
                hops.append({
                    'hop': hop,
                    'url': current_url,
                    'status_code': 0,
                    'redirect_to': None,
                    'final': True,
                })
                done = True
            finally:
                if response:
                    response.close()
            if done:
                break

        return {'hops': hops}

    except Exception as e:
        print(f"redirects collector total failure for {target}: {e}", file=sys.stderr)
        return {}
