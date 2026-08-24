# Testing, Debugging, and Code Review Reference

## Testing strategy

Tests should provide confidence at the lowest sustainable cost.

- Unit tests: business rules, pure functions, validation, transformations, edge cases
- Component tests: modules with real internal behavior and controlled external boundaries
- Integration tests: databases, queues, filesystems, caches, and service contracts
- End-to-end tests: a small number of critical user journeys
- Contract tests: compatibility between independently deployed producers and consumers
- Performance tests: latency, throughput, concurrency, resource usage, and degradation
- Security tests: authorization, input abuse, tenant isolation, secret exposure, and dependency checks
- Resilience tests: timeouts, dependency failure, retry behavior, restart, and recovery

Avoid testing implementation details that make harmless refactors expensive. Test public behavior, invariants, and important failure cases.

## Test case checklist

For each feature consider:

- Happy path
- Empty, null, minimum, maximum, and boundary values
- Invalid types and malformed input
- Duplicate and retry behavior
- Concurrency and race conditions
- Permission denied and cross-tenant access
- Dependency timeout and partial failure
- Database constraint or transaction failure
- Localization, timezone, encoding, and large input
- Accessibility and keyboard interaction for UI
- Backward compatibility
- Logging and metrics behavior

## Test quality

- Tests must be deterministic and isolated.
- Control time, randomness, network, and external dependencies.
- Do not depend on execution order.
- Use realistic fixtures without secrets or personal data.
- Keep assertions specific enough to explain failures.
- Quarantine or repair flaky tests; do not normalize them.
- Track coverage as a signal, not a substitute for meaningful assertions.

## Debugging workflow

1. Restate the exact symptom and expected behavior.
2. Gather the smallest reproducible case.
3. Record environment, versions, configuration, inputs, and recent changes.
4. Separate observations from assumptions.
5. Form ranked hypotheses.
6. Add targeted logging, tracing, breakpoints, or probes.
7. Change one variable at a time.
8. Apply the smallest fix that addresses the root cause.
9. Add a regression test.
10. Verify in an environment representative of the failure.
11. Document prevention when the issue could recur.

Useful evidence includes complete error messages, stack traces, timestamps, correlation IDs, relevant configuration, dependency versions, request/response samples with secrets redacted, and a minimal code sample.

## Code review dimensions

Review changes for:

- Requirement and acceptance-criteria correctness
- Edge cases and failure handling
- Security, privacy, authentication, and authorization
- Data integrity and migration safety
- API and event compatibility
- Concurrency, idempotency, and transaction boundaries
- Performance and resource behavior
- Reliability, observability, and operability
- Maintainability, clarity, and unnecessary complexity
- Dependency and supply-chain risk
- Test completeness and quality
- Accessibility and responsive behavior
- Deployment, feature flags, and rollback

## Severity definitions

- Blocker: likely catastrophic impact, active exploitable risk, data loss, or change cannot safely ship
- High: serious correctness, security, availability, or compatibility risk requiring resolution before release
- Medium: meaningful defect or maintainability/operability issue that should be fixed soon
- Low: limited impact, minor robustness issue, or useful improvement
- Nit: stylistic or optional suggestion with no material risk

## Review finding template

```text
Severity:
Location:
Problem:
Impact:
Why it happens:
Recommended patch:
Test to add:
```

## Performance investigation

- Define the user-visible or operational objective.
- Measure baseline latency, throughput, error rate, saturation, memory, CPU, I/O, and database behavior.
- Use profiles and traces before optimizing.
- Check query count, indexes, allocations, serialization, network fan-out, locks, and cache behavior.
- Optimize the demonstrated bottleneck.
- Re-measure and check correctness after every material change.

## Accessibility review for user interfaces

- Semantic structure and labels
- Keyboard access and visible focus
- Screen-reader names and status announcements
- Color-independent meaning and sufficient contrast
- Zoom and responsive layouts
- Error identification and recovery
- Reduced-motion support where appropriate
- Automated checks plus manual keyboard and assistive-technology testing
