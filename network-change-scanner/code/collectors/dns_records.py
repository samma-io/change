import sys

import dns.resolver


def collect(target: str, config: dict) -> dict:
    """
    Returns: {"A": [...], "AAAA": [...], "MX": [...], "TXT": [...], "NS": [...]}
    Per record type: list of string values, or [] if no answer.
    On total failure: return {}
    """
    try:
        record_types = config.get('dns_record_types', ['A', 'AAAA', 'MX', 'TXT', 'NS'])

        resolver = dns.resolver.Resolver()
        resolver.lifetime = float(config.get('timeout', 5))

        result = {}
        for rtype in record_types:
            try:
                answers = resolver.resolve(target, rtype)
                result[rtype] = [rdata.to_text() for rdata in answers]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                result[rtype] = []
            except Exception as e:
                print(f"dns_records collector error for {target} {rtype}: {e}", file=sys.stderr)
                result[rtype] = []

        return result

    except Exception as e:
        print(f"dns_records collector total failure for {target}: {e}", file=sys.stderr)
        return {}
