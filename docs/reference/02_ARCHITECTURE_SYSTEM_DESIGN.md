# Architecture and System Design Reference

## Start with requirements

Before selecting technologies, capture:

- Primary users and jobs to be done
- Functional requirements and explicit non-goals
- Expected traffic, data volume, growth, and concurrency
- Latency and availability objectives
- Consistency and durability needs
- Security, privacy, residency, and compliance constraints
- Budget, team skills, delivery timeline, and operational capacity
- Existing systems, integrations, and migration constraints

Unknown values should be labeled as assumptions and tested through discovery or measurement.

## Design principles

- Prefer a modular monolith for a new product unless independent scaling, deployment, ownership, isolation, or regulatory boundaries justify services.
- Keep domain logic independent from transport and storage details where practical.
- Define clear component ownership and contracts.
- Make external calls observable, time-bounded, retried only when safe, and protected against cascading failure.
- Use asynchronous processing for work that need not block a user request.
- Introduce queues, caches, search engines, event streams, and distributed coordination only for a demonstrated requirement.
- Design for safe migration and rollback from the beginning.

## Standard architecture areas

A complete system design should consider:

1. Clients: web, mobile, desktop, devices, partner systems
2. Edge: DNS, CDN, WAF, rate limiting, load balancing
3. Application: APIs, background workers, scheduled jobs, domain modules
4. Data: transactional database, object storage, cache, search, analytics
5. Integration: third-party APIs, webhooks, events, queues
6. Identity: authentication, authorization, sessions, service identities
7. Operations: CI/CD, configuration, secrets, observability, support tooling
8. Trust boundaries: public, partner, internal, privileged, and data-processing zones

## Data and consistency decisions

For every important entity or event, define:

- Source of truth
- Ownership
- Schema and invariants
- Read and write patterns
- Transaction boundary
- Consistency expectation
- Retention, archival, and deletion policy
- Backup and recovery objectives
- Audit requirements

Avoid dual writes across independent systems. Prefer a transactional outbox, change-data capture, or another explicit consistency pattern when a database update and event publication must agree.

## Reliability patterns

Use according to failure mode:

- Timeouts on network calls
- Bounded retries with exponential backoff and jitter
- Idempotency for retryable writes
- Circuit breakers for unhealthy dependencies
- Bulkheads and concurrency limits
- Dead-letter handling for failed messages
- Graceful degradation and feature flags
- Health checks that distinguish process health from dependency readiness
- Multi-zone deployment where availability objectives require it

Retry only transient failures. Do not blindly retry non-idempotent operations.

## Scaling checklist

- Identify the actual bottleneck with metrics.
- Scale stateless compute horizontally where useful.
- Add database indexes from measured query patterns.
- Use connection pooling and protect databases from unbounded concurrency.
- Cache stable or expensive reads with explicit invalidation and TTL behavior.
- Partition data only when single-node or single-partition limits are demonstrated.
- Use backpressure and admission control under overload.
- Plan capacity around peak load, failure scenarios, and growth.

## Security and privacy by design

Document assets, actors, trust boundaries, attack surfaces, data sensitivity, and abuse cases. Apply least privilege, encryption in transit and at rest, secure secret storage, audit logging, input validation, rate limits, and tenant isolation. Minimize collection and retention of personal or confidential data.

## Observability

Define:

- Structured logs with correlation identifiers
- Metrics for traffic, errors, latency, saturation, and business outcomes
- Distributed traces across important service boundaries
- Dashboards tied to service objectives
- Alerts that are actionable and have owners/runbooks
- Audit logs for sensitive administrative operations

## Architecture Decision Record template

```text
Title:
Status: Proposed | Accepted | Deprecated | Superseded
Date:
Context:
Decision drivers:
Options considered:
Decision:
Consequences and trade-offs:
Security/privacy impact:
Operational impact:
Migration plan:
Rollback plan:
Validation criteria:
```

## System design response template

```text
1. Goals and non-goals
2. Assumptions and scale
3. Proposed architecture
4. Component responsibilities
5. Data model and storage choices
6. API/event contracts
7. Critical request and data flows
8. Security and privacy
9. Reliability and scaling
10. Observability and operations
11. Deployment, migration, and rollback
12. Cost drivers
13. Alternatives and trade-offs
14. Open questions and validation plan
```
