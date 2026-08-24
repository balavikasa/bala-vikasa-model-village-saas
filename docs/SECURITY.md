# Security and privacy controls

- Passwords use Werkzeug's adaptive password hashing; plaintext passwords are never stored.
- Flask-Login sessions use HttpOnly, SameSite=Lax cookies and should use `Secure` behind HTTPS.
- All mutating browser/API requests require CSRF tokens.
- Authorization is deny-by-default and centralized in `app/scoping.py`.
- PM is read-only. PC and DA permissions are separately checked from row visibility.
- Parent moves are explicit, audited, and blocked when they would invalidate historical submissions.
- Audit records are append-only through the application layer.
- Photo names are generated; paths supplied by clients are never used.
- Uploaded images are decoded and re-encoded, stripping metadata.
- Security headers include CSP, frame restrictions, MIME sniffing protection, referrer policy, and
  permissions policy.
- Secrets belong in environment variables or a secret manager. Rotate the bootstrap admin password
  immediately and unset the bootstrap variables.
- Reverse proxies must only be trusted when `TRUST_PROXY_HEADERS=true` and when the application is
  actually behind a controlled proxy.
- Logs must not contain passwords, session cookies, full CSRF tokens, or raw photos.

## Production checklist

Terminate TLS at a trusted ingress, set `SESSION_COOKIE_SECURE=true`, restrict database and upload
access to the application identity, disable debug mode, rate-limit login at the ingress, scan
dependencies and images in CI, monitor repeated authentication failures, and test restore procedures
before launch.
