# Project Context Template

Customize this file before uploading it as Knowledge. Remove placeholder sections that do not apply. Never include secrets, credentials, private keys, production tokens, or data users are not authorized to access.

## Product summary

- Product name: [ADD]
- One-sentence purpose: [ADD]
- Primary users: [ADD]
- Main user journeys: [ADD]
- Business objectives: [ADD]
- Explicit non-goals: [ADD]

## Domain terminology

| Term | Meaning |
|---|---|
| [TERM] | [DEFINITION] |
| [TERM] | [DEFINITION] |

## User roles and permissions

| Role | Allowed actions | Prohibited or restricted actions |
|---|---|---|
| [ROLE] | [ADD] | [ADD] |

Describe tenant boundaries, ownership rules, administrative roles, support impersonation, and approval workflows here: [ADD]

## Approved technology stack

- Frontend: [framework, language, versions]
- Backend: [framework, language, versions]
- Mobile/desktop: [ADD]
- API style: [REST/GraphQL/gRPC/events]
- Primary database: [ADD]
- Cache/search/queue: [ADD]
- Data platform: [ADD]
- AI/ML platform: [ADD]
- Cloud provider and regions: [ADD]
- Containers/orchestration: [ADD]
- Infrastructure as code: [ADD]
- CI/CD: [ADD]
- Monitoring and incident tools: [ADD]
- Identity provider: [ADD]
- Secret manager: [ADD]

## Prohibited or discouraged technologies

- [TECHNOLOGY]: [REASON]
- [TECHNOLOGY]: [REASON]

## Repository map

```text
[repository-root]/
  [directory]/  - [purpose]
  [directory]/  - [purpose]
```

- Main entry points: [ADD]
- Shared libraries: [ADD]
- Test locations: [ADD]
- Migration locations: [ADD]
- Deployment configuration: [ADD]

## Coding conventions

- Naming: [ADD]
- Formatting/linting: [ADD]
- Type checking: [ADD]
- Error-handling pattern: [ADD]
- Logging pattern: [ADD]
- Dependency policy: [ADD]
- Documentation style: [ADD]
- Commit and pull-request conventions: [ADD]

## Architecture summary

- Architecture style: [ADD]
- Major components and owners: [ADD]
- Critical request flows: [ADD]
- Sources of truth: [ADD]
- External integrations: [ADD]
- Event topics/queues: [ADD]
- Trust boundaries: [ADD]
- Known bottlenecks or technical debt: [ADD]

Add or link a Mermaid diagram using only non-sensitive names when useful.

## API conventions

- Base URL pattern: [ADD]
- Authentication: [ADD]
- Authorization: [ADD]
- Versioning: [ADD]
- Pagination: [ADD]
- Error format: [ADD]
- Idempotency: [ADD]
- Rate limits: [ADD]
- Deprecation policy: [ADD]

## Data model

List core entities and relationships:

| Entity | Purpose | Owner/source of truth | Sensitive fields | Retention |
|---|---|---|---|---|
| [ENTITY] | [ADD] | [ADD] | [ADD] | [ADD] |

- Database naming conventions: [ADD]
- Migration process: [ADD]
- Backup and restore requirements: [ADD]
- Data residency and deletion requirements: [ADD]

## Security and privacy requirements

- Data classification scheme: [ADD]
- Authentication requirements: [ADD]
- Authorization model: [ADD]
- Encryption requirements: [ADD]
- Audit logging: [ADD]
- Secrets policy: [ADD]
- Regulatory/contractual constraints: [ADD]
- Security review triggers: [ADD]
- Vulnerability remediation targets: [ADD]

Do not include confidential threat details unless every GPT user is authorized to read them.

## Testing requirements

- Required unit tests: [ADD]
- Required integration tests: [ADD]
- Required end-to-end tests: [ADD]
- Coverage expectations: [ADD]
- Performance targets: [ADD]
- Accessibility standard: [ADD]
- Test-data restrictions: [ADD]
- CI quality gates: [ADD]

## Deployment and operations

- Environments: [ADD]
- Release cadence: [ADD]
- Deployment strategy: [ADD]
- Feature flag approach: [ADD]
- Health checks: [ADD]
- Key dashboards and alerts: [ADD]
- Service-level objectives: [ADD]
- On-call/escalation: [ADD]
- Backup and disaster recovery objectives: [ADD]
- Rollback procedure: [ADD]

## Current roadmap and constraints

- Current milestone: [ADD]
- Near-term priorities: [ADD]
- Deadline constraints: [ADD]
- Budget constraints: [ADD]
- Team skill constraints: [ADD]
- Compatibility constraints: [ADD]
- Decisions already made and not open for debate: [ADD]

## Architecture decisions

Summarize accepted decisions or attach separate ADR files:

| Decision | Status | Rationale | Date |
|---|---|---|---|
| [ADD] | Accepted | [ADD] | [YYYY-MM-DD] |

## Useful non-secret examples

- Representative API request/response: [ADD]
- Representative configuration with fake values: [ADD]
- Common error codes: [ADD]
- Common troubleshooting cases: [ADD]
