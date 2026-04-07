import sys
import datetime
import socket as _socket

import whois


def collect(target: str, config: dict) -> dict:
    """
    Returns:
    {
      "registrar": str | None, "creation_date": str | None,
      "expiration_date": str | None, "name_servers": [str]
    }
    Dates as "YYYY-MM-DD" strings (not datetime objects).
    On error: return {}
    """
    try:
        def to_date_str(v):
            """Convert a datetime or list of datetimes to YYYY-MM-DD string."""
            if v is None:
                return None
            if isinstance(v, list):
                v = v[0] if v else None
            if v is None:
                return None
            if isinstance(v, datetime.datetime):
                return v.strftime('%Y-%m-%d')
            if isinstance(v, datetime.date):
                return v.strftime('%Y-%m-%d')
            # Try parsing string representations
            s = str(v)
            try:
                return datetime.datetime.strptime(s[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                return s

        def first_or_str(v):
            if v is None:
                return None
            if isinstance(v, list):
                return str(v[0]) if v else None
            return str(v)

        old_timeout = _socket.getdefaulttimeout()
        _socket.setdefaulttimeout(float(config.get('timeout', 10)))
        try:
            w = whois.whois(target)
        finally:
            _socket.setdefaulttimeout(old_timeout)

        name_servers = w.name_servers
        if isinstance(name_servers, list):
            ns_list = [str(n).lower() for n in name_servers if n]
        elif name_servers:
            ns_list = [str(name_servers).lower()]
        else:
            ns_list = []

        return {
            'registrar': first_or_str(w.registrar),
            'creation_date': to_date_str(w.creation_date),
            'expiration_date': to_date_str(w.expiration_date),
            'name_servers': ns_list,
        }

    except Exception as e:
        print(f"whois_info collector error for {target}: {e}", file=sys.stderr)
        return {}
