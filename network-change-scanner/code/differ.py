"""
differ.py — Snapshot comparison module for network-change-scanner.

Compares a baseline snapshot against a current snapshot and returns a list of
findings, one dict per detected change.
"""

from __future__ import annotations


def compare(baseline: dict, current: dict) -> list[dict]:
    """
    Compare two snapshots and return a list of change findings.

    Args:
        baseline: The reference snapshot dict.
        current:  The new snapshot dict to compare against baseline.

    Returns:
        A list of finding dicts. Empty list if no changes detected.
        Never raises.
    """
    findings: list[dict] = []

    _compare_tls(baseline, current, findings)
    _compare_dns(baseline, current, findings)
    _compare_http_headers(baseline, current, findings)
    _compare_ports(baseline, current, findings)
    _compare_traceroute(baseline, current, findings)
    _compare_ssh_banner(baseline, current, findings)
    _compare_redirects(baseline, current, findings)
    _compare_whois(baseline, current, findings)

    return findings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finding(category: str, field: str, change_type: str, old_value, new_value) -> dict:
    return {
        "category": category,
        "field": field,
        "change_type": change_type,
        "old_value": old_value,
        "new_value": new_value,
    }


# ---------------------------------------------------------------------------
# Per-category comparators
# ---------------------------------------------------------------------------

_TLS_IGNORED = {"days_remaining"}

def _compare_tls(baseline: dict, current: dict, findings: list) -> None:
    try:
        old = baseline.get("tls", {})
        new = current.get("tls", {})

        if not old and not new:
            return

        # If both sides carry an "error" key, nothing meaningful to compare.
        old_has_error = "error" in old
        new_has_error = "error" in new

        if old_has_error and new_has_error:
            return

        # If exactly one side has an error, report the banner field as modified.
        if old_has_error != new_has_error:
            findings.append(_finding(
                "tls", "error",
                "modified",
                old.get("error") if old_has_error else None,
                new.get("error") if new_has_error else None,
            ))
            return

        all_keys = set(old.keys()) | set(new.keys())
        for field in all_keys:
            if field in _TLS_IGNORED:
                continue
            old_val = old.get(field)
            new_val = new.get(field)
            if old_val != new_val:
                findings.append(_finding("tls", field, "modified", old_val, new_val))

    except Exception:
        pass


def _compare_dns(baseline: dict, current: dict, findings: list) -> None:
    try:
        old = baseline.get("dns", {})
        new = current.get("dns", {})

        all_record_types = set(old.keys()) | set(new.keys())

        for rtype in all_record_types:
            old_values = set(old.get(rtype, []))
            new_values = set(new.get(rtype, []))

            for val in sorted(old_values - new_values):
                findings.append(_finding("dns", rtype, "removed", val, None))

            for val in sorted(new_values - old_values):
                findings.append(_finding("dns", rtype, "added", None, val))

    except Exception:
        pass


_HTTP_IGNORED = {
    "date", "age", "expires", "last-modified",
    "cf-ray", "x-request-id", "x-amz-request-id", "x-amzn-requestid",
    "x-cache", "x-cache-hits", "via", "set-cookie",
}

def _compare_http_headers(baseline: dict, current: dict, findings: list) -> None:
    try:
        old = baseline.get("http_headers", {})
        new = current.get("http_headers", {})

        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            # Normalise to lowercase for ignore-list check, but preserve the
            # original key name in the finding.
            if key.lower() in _HTTP_IGNORED:
                continue

            old_val = old.get(key)
            new_val = new.get(key)

            if old_val == new_val:
                continue

            if key not in old:
                findings.append(_finding("http_headers", key, "added", None, new_val))
            elif key not in new:
                findings.append(_finding("http_headers", key, "removed", old_val, None))
            else:
                findings.append(_finding("http_headers", key, "modified", old_val, new_val))

    except Exception:
        pass


def _compare_ports(baseline: dict, current: dict, findings: list) -> None:
    try:
        old = baseline.get("ports", {})
        new = current.get("ports", {})

        all_ports = set(old.keys()) | set(new.keys())

        for port in all_ports:
            old_state = old.get(port)
            new_state = new.get(port)

            # If either side is an error, skip.
            if old_state == "error" or new_state == "error":
                continue

            if old_state == new_state:
                continue

            if old_state is None:
                findings.append(_finding("ports", port, "added", None, new_state))
            elif new_state is None:
                findings.append(_finding("ports", port, "removed", old_state, None))
            else:
                findings.append(_finding("ports", port, "modified", old_state, new_state))

    except Exception:
        pass


def _compare_traceroute(baseline: dict, current: dict, findings: list) -> None:
    try:
        old = baseline.get("traceroute", {})
        new = current.get("traceroute", {})

        old_hops = old.get("hops", [])
        new_hops = new.get("hops", [])

        if len(old_hops) != len(new_hops):
            findings.append(_finding(
                "traceroute", "hop_count", "modified",
                len(old_hops), len(new_hops),
            ))

        for i, (old_hop, new_hop) in enumerate(zip(old_hops, new_hops)):
            hop_num = old_hop.get("hop", i + 1)
            old_ip = old_hop.get("ip")
            new_ip = new_hop.get("ip")

            if old_ip != new_ip:
                findings.append(_finding(
                    "traceroute", f"hop_{hop_num}_ip", "modified",
                    old_ip, new_ip,
                ))

    except Exception:
        pass


def _compare_ssh_banner(baseline: dict, current: dict, findings: list) -> None:
    try:
        old = baseline.get("ssh_banner", {})
        new = current.get("ssh_banner", {})

        if not old and not new:
            return

        old_has_error = "error" in old
        new_has_error = "error" in new

        # Both sides errored — nothing useful to compare.
        if old_has_error and new_has_error:
            return

        # One side has an error, the other doesn't — treat as banner change.
        if old_has_error != new_has_error:
            old_banner = old.get("banner") if not old_has_error else old.get("error")
            new_banner = new.get("banner") if not new_has_error else new.get("error")
            findings.append(_finding("ssh_banner", "banner", "modified", old_banner, new_banner))
            return

        for field in ("banner", "software"):
            old_val = old.get(field)
            new_val = new.get(field)
            if old_val != new_val:
                findings.append(_finding("ssh_banner", field, "modified", old_val, new_val))

    except Exception:
        pass


def _compare_redirects(baseline: dict, current: dict, findings: list) -> None:
    try:
        old = baseline.get("redirects", {})
        new = current.get("redirects", {})

        old_hops = old.get("hops", [])
        new_hops = new.get("hops", [])

        if len(old_hops) != len(new_hops):
            findings.append(_finding(
                "redirects", "hop_count", "modified",
                len(old_hops), len(new_hops),
            ))

        for i, (old_hop, new_hop) in enumerate(zip(old_hops, new_hops)):
            hop_num = old_hop.get("hop", i + 1)

            for subfield in ("url", "status_code", "redirect_to"):
                old_val = old_hop.get(subfield)
                new_val = new_hop.get(subfield)
                if old_val != new_val:
                    findings.append(_finding(
                        "redirects", f"hop_{hop_num}_{subfield}", "modified",
                        old_val, new_val,
                    ))

    except Exception:
        pass


def _compare_whois(baseline: dict, current: dict, findings: list) -> None:
    try:
        old = baseline.get("whois", {})
        new = current.get("whois", {})

        for field in ("registrar", "creation_date", "expiration_date"):
            old_val = old.get(field)
            new_val = new.get(field)
            if old_val != new_val:
                findings.append(_finding("whois", field, "modified", old_val, new_val))

        old_ns = set(old.get("name_servers") or [])
        new_ns = set(new.get("name_servers") or [])

        for ns in sorted(old_ns - new_ns):
            findings.append(_finding("whois", "name_servers", "removed", ns, None))

        for ns in sorted(new_ns - old_ns):
            findings.append(_finding("whois", "name_servers", "added", None, ns))

    except Exception:
        pass
