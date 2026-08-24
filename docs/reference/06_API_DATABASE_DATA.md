# API, Database, and Data Engineering Reference

## API design

Choose the interface style that matches the need:

- REST for resource-oriented public or internal HTTP APIs
- GraphQL for flexible client-driven querying with strong governance
- gRPC for typed, efficient service-to-service communication
- Events or queues for asynchronous workflows and decoupling
- Webhooks for outbound event notification to external consumers

Do not mix styles without a clear benefit.

## API contract checklist

Define:

- Endpoint or method name and purpose
- Authentication and authorization requirements
- Request fields, types, validation, and size limits
- Response schema and status behavior
- Stable machine-readable errors
- Idempotency and retry semantics
- Pagination, filtering, sorting, and search behavior
- Rate limits and quota headers where relevant
- Versioning and deprecation policy
- Examples with synthetic data

## HTTP guidance

- Use nouns for resources and standard methods consistently.
- Use appropriate status codes, but keep error bodies consistent.
- Validate content type and body size.
- Use cursor pagination for large or frequently changing collections.
- Support idempotency keys for retry-prone create or payment-like operations.
- Use conditional requests or version fields for concurrent updates where useful.
- Do not place secrets or sensitive personal information in URLs.
- Set explicit timeouts for clients and servers.

Example error shape:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found.",
    "details": {},
    "request_id": "synthetic-request-id"
  }
}
```

## Webhooks

- Sign payloads and include a timestamp.
- Reject expired or replayed requests.
- Deliver at least once and document duplicate handling.
- Retry transient failures with backoff and a bounded retention period.
- Provide event identifiers and versioned schemas.
- Do not assume event order unless guaranteed.
- Expose delivery logs or a replay mechanism when appropriate.

## Relational database design

- Choose keys deliberately and enforce invariants with constraints.
- Normalize transactional data until measured access patterns justify selective denormalization.
- Use foreign keys when compatible with the scale and ownership model.
- Add indexes for demonstrated queries; remember every index has write and storage cost.
- Keep transactions short and define isolation requirements.
- Use parameterized queries and least-privileged database roles.
- Avoid unbounded queries and application-side N+1 access patterns.
- Store timestamps with clear timezone semantics, normally UTC internally.

## Schema migrations

Safe deployment sequence for many changes:

1. Expand: add backward-compatible schema or columns.
2. Deploy code that can read/write both old and new forms.
3. Backfill in bounded observable batches.
4. Switch reads or behavior after validation.
5. Contract: remove obsolete structures only after all consumers migrate.

For every migration define locking risk, runtime, index-build strategy, backup/recovery, compatibility window, verification queries, and rollback or forward-recovery plan.

## NoSQL and specialized stores

Use a specialized store because its access model or operational properties are required, not because it is fashionable. Document partition key, query patterns, consistency, size limits, hot-key risk, secondary indexes, retention, backup, and migration strategy.

## Caching

- Define what is cached, why, key structure, TTL, ownership, and invalidation.
- Treat cache as disposable unless explicitly designed as durable state.
- Prevent stampedes with request coalescing, jitter, or locking where needed.
- Avoid caching authorization decisions longer than their safe validity.
- Monitor hit rate, latency, evictions, memory, and stale-data impact.

## Data pipelines

For each pipeline define:

- Source and owner
- Schema and contract
- Ingestion frequency or event semantics
- Validation and quality checks
- Deduplication and idempotency
- Late and out-of-order data behavior
- Lineage and transformations
- Storage, partitioning, and retention
- Privacy classification and access
- Freshness and completeness objectives
- Reprocessing and backfill plan
- Monitoring and alerting

## Data quality dimensions

- Completeness
- Validity
- Accuracy
- Consistency
- Uniqueness
- Timeliness
- Referential integrity

Fail or quarantine data according to business impact. Do not silently discard malformed records without metrics and an investigation path.
