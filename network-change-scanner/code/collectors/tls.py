import sys
import ssl
import socket
import datetime


def collect(target: str, config: dict) -> dict:
    """
    Returns:
    {
      "valid": bool, "expired": bool, "days_remaining": int,
      "expires": "YYYY-MM-DD", "subject_cn": str,
      "issuer": str, "protocol": str, "cipher": str
    }
    On error: return {"error": str(e)}
    """
    try:
        port = int(config.get('tls_port', 443))
        timeout = int(config.get('timeout', 5))
        verify_cert_val = config.get('verify_cert', True)
        if isinstance(verify_cert_val, str):
            verify_cert = verify_cert_val.lower() not in ('false', '0', 'no')
        else:
            verify_cert = bool(verify_cert_val)

        context = ssl.create_default_context() if verify_cert else ssl._create_unverified_context()

        with socket.create_connection((target, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=target) as ssock:
                cert = ssock.getpeercert()
                cipher_info = ssock.cipher()
                protocol = ssock.version()

                # Parse expiry
                not_after_str = cert.get('notAfter', '')
                not_after = datetime.datetime.strptime(not_after_str, '%b %d %H:%M:%S %Y %Z')
                now = datetime.datetime.utcnow()
                days_remaining = (not_after - now).days
                expired = days_remaining < 0

                # Subject CN
                subject_cn = None
                for field in cert.get('subject', []):
                    for key, value in field:
                        if key == 'commonName':
                            subject_cn = value

                # Issuer organisation
                issuer = None
                for field in cert.get('issuer', []):
                    for key, value in field:
                        if key == 'organizationName':
                            issuer = value

                return {
                    'valid': True,
                    'expired': expired,
                    'days_remaining': days_remaining,
                    'expires': not_after.strftime('%Y-%m-%d'),
                    'subject_cn': subject_cn,
                    'issuer': issuer,
                    'protocol': protocol,
                    'cipher': cipher_info[0] if cipher_info else None,
                }

    except ssl.SSLCertVerificationError as e:
        print(f"tls collector SSLCertVerificationError for {target}: {e}", file=sys.stderr)
        return {'error': str(e)}
    except Exception as e:
        print(f"tls collector error for {target}: {e}", file=sys.stderr)
        return {'error': str(e)}
