# Engineering Standards

This document is a general software engineering reference. Replace bracketed values with organization-specific rules when available.

## Core principles

1. Correctness before cleverness.
2. Prefer the simplest design that satisfies present requirements.
3. Make behavior explicit through types, validation, contracts, and tests.
4. Optimize for readability, maintainability, security, and operability.
5. Automate repetitive checks and make builds reproducible.
6. Preserve backward compatibility unless a breaking change is intentional and documented.
7. Measure before optimizing.

## Repository organization

A repository should make the main workflows easy to discover. Recommended top-level areas:

- `src/` or language-standard application directories
- `tests/` for unit and integration tests when not colocated
- `docs/` for architecture, operations, and decisions
- `scripts/` for repeatable developer or operational tasks
- `migrations/` for versioned database changes
- `.github/` or equivalent CI configuration
- `README.md` with setup, run, test, build, and troubleshooting steps
- `.env.example` containing names and safe examples, never real secrets

Follow the existing repository structure before introducing a new convention.

## Code quality

- Use descriptive names and small cohesive functions.
- Keep modules focused on one responsibility.
- Prefer explicit interfaces and dependency injection at external boundaries.
- Avoid hidden global state and unnecessary mutable state.
- Handle expected failures deliberately; do not swallow exceptions.
- Add context to errors without exposing secrets or personal data.
- Use structured logging where supported.
- Remove dead code, unused dependencies, and commented-out implementations.
- Document non-obvious decisions and public interfaces, not obvious syntax.
- Use automated formatting, linting, type checking, and tests in CI.

## Dependency policy

Before adding a dependency, assess:

- Whether the platform standard library or an existing dependency already solves the problem
- Maintenance activity, license, security record, ecosystem adoption, and release cadence
- Transitive dependency and bundle-size impact
- Upgrade and removal cost

Pin or lock dependencies using the ecosystem-standard lockfile. Automate vulnerability scanning and dependency updates. Avoid unmaintained packages for security-sensitive functionality.

## Configuration and secrets

- Keep configuration outside application code.
- Validate configuration at startup and fail with a clear message.
- Separate development, test, staging, and production values.
- Store secrets in an approved secret manager, not source control.
- Rotate credentials and support overlapping keys where zero-downtime rotation is required.
- Never log tokens, passwords, private keys, raw session identifiers, or full payment data.

## API and compatibility discipline

- Define stable contracts and validate inputs and outputs.
- Prefer additive changes over breaking changes.
- Version externally consumed contracts when compatibility cannot be preserved.
- Provide deprecation notices, migration guidance, and a removal date.
- Use consistent error formats and machine-readable error codes.

## Git and pull requests

Recommended branch and review practices:

- Keep changes small enough to review confidently.
- Write commit messages that explain intent.
- Link changes to an issue, requirement, or incident when applicable.
- Include tests and documentation in the same change.
- Require review for production-bound changes.
- Resolve all Blocker and High findings before merge.
- Use protected branches and CI status checks.

Pull request description template:

```text
Summary:
Why this change is needed:
Implementation approach:
Security/privacy impact:
Database/API compatibility impact:
Test evidence:
Deployment plan:
Rollback plan:
Screenshots or logs, with secrets redacted:
```

## Definition of done

A change is done when applicable requirements are met:

- Acceptance criteria pass
- Code is formatted, linted, type-checked, and reviewed
- Unit/integration/end-to-end tests pass
- Security and privacy implications are addressed
- Database migrations are safe and reversible or have a recovery plan
- API compatibility is verified
- Documentation and examples are updated
- Logs, metrics, health checks, and alerts are adequate
- Deployment and rollback steps are known
- No credentials, debug artifacts, or sensitive data are committed

## Organization-specific overrides

Fill these in before uploading when relevant:

- Preferred languages and versions: [ADD]
- Preferred frameworks: [ADD]
- Package managers: [ADD]
- Formatter/linter/type checker: [ADD]
- Minimum test expectations: [ADD]
- Branching and release strategy: [ADD]
- Documentation standard: [ADD]
- Approved and prohibited dependencies: [ADD]
