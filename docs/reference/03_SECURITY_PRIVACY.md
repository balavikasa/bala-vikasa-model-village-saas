# Secure Engineering and Privacy Reference

This document supports secure development, defensive analysis, threat modeling, and authorized testing.

## Security foundations

- Treat all external input as untrusted.
- Authenticate identities and authorize every protected action separately.
- Deny by default and apply least privilege to users, services, networks, and data.
- Keep secrets out of source code, logs, tickets, screenshots, and client bundles.
- Use established cryptographic libraries and modern platform defaults.
- Minimize sensitive data collection, access, retention, and replication.
- Log security-relevant events without logging secret values.
- Patch supported systems and remove unsupported components.
- Design controls in layers; do not rely on one perimeter.

## Threat modeling checklist

For each feature identify:

1. Assets: data, identities, money, compute, availability, intellectual property
2. Actors: anonymous users, authenticated users, admins, services, insiders, partners
3. Entry points: APIs, UI, files, webhooks, queues, jobs, admin tools, support workflows
4. Trust boundaries: client/server, tenant, network, account, environment, third party
5. Abuse cases: spoofing, tampering, repudiation, data disclosure, denial of service, privilege escalation, business-logic abuse
6. Controls: prevention, detection, response, recovery
7. Residual risk, owner, and review date

## Authentication

- Prefer mature identity providers and standard protocols.
- Require multi-factor authentication for privileged access.
- Store passwords only with an approved adaptive password-hashing algorithm.
- Rate-limit and monitor login, recovery, enrollment, and verification endpoints.
- Make account recovery at least as secure as login.
- Rotate sessions after authentication and privilege changes.
- Use short-lived tokens where practical and validate issuer, audience, signature, expiry, and intended use.

## Authorization

- Enforce authorization on the server for every protected resource and action.
- Check object ownership or tenant membership, not only user role.
- Avoid trusting identifiers or roles sent by clients.
- Centralize policy where practical and test deny cases.
- Require re-authentication or stronger approval for high-risk actions.
- Audit privileged and cross-tenant operations.

## Web, API, and input safety

- Use allow-list validation for types, ranges, lengths, formats, and state transitions.
- Encode output for its destination context.
- Use parameterized database queries.
- Protect state-changing browser requests against cross-site request forgery when cookies are used.
- Restrict CORS to required origins, methods, and headers.
- Use secure cookie attributes and appropriate content security policy.
- Validate content type and size for uploads; store outside executable paths; scan when risk warrants it.
- Verify webhook signatures, timestamps, replay protection, and source expectations.
- Apply per-user, per-tenant, and global rate limits where abuse is possible.
- Never expose internal stack traces or secret configuration in client errors.

## Secrets and cryptography

- Store production secrets in an approved secret manager.
- Separate secrets by environment and workload.
- Grant access to individual workloads rather than broad teams where possible.
- Support rotation and emergency revocation.
- Encrypt data in transit and at rest using platform-supported mechanisms.
- Do not design custom encryption, token formats, or key derivation.
- Define key ownership, rotation, backup, and destruction procedures.

## Software supply chain

- Use lockfiles and verified registries.
- Review new dependencies for maintenance, license, transitive risk, and necessity.
- Scan source, dependencies, containers, and infrastructure definitions.
- Protect CI credentials and restrict pull-request access to secrets.
- Generate or retain build provenance and software bills of materials where required.
- Sign release artifacts where the platform supports it.
- Pin third-party CI actions or plugins to trusted immutable versions.

## Cloud and infrastructure

- Separate accounts/projects/subscriptions for production and non-production.
- Disable public access by default.
- Use workload identity instead of long-lived static keys where available.
- Restrict network paths and administrative interfaces.
- Encrypt backups and test restoration.
- Detect configuration drift and unauthorized changes.
- Centralize security logs and protect them from alteration.

## Privacy and data handling

Classify data as appropriate for the organization, for example:

- Public
- Internal
- Confidential
- Restricted

For personal or regulated data define purpose, legal/organizational basis, fields collected, access, storage locations, retention, deletion, export, audit, and incident obligations. Redact or tokenize sensitive values in lower environments. Do not use production personal data in tests unless explicitly approved and protected.

## Security review output

For every finding include:

```text
Severity: Blocker | High | Medium | Low | Informational
Location:
Issue:
Attack or failure scenario:
Impact:
Evidence:
Recommended fix:
Verification test:
Residual risk:
```

## Incident basics

1. Stabilize and limit impact.
2. Preserve evidence and maintain a timeline.
3. Revoke or rotate compromised access.
4. Identify affected systems and data.
5. Recover through known-good builds and configurations.
6. Notify required stakeholders through approved channels.
7. Complete root-cause analysis and track preventive actions.

Do not place real secrets, exploit material against unauthorized targets, unredacted customer data, or confidential vulnerability details in this knowledge file.
