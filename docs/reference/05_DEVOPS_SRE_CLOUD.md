# DevOps, SRE, and Cloud Operations Reference

## Environment strategy

Maintain explicit development, test, staging, and production environments as needed. Production should use controlled identities, networks, secrets, data, and deployment paths. Avoid making staging a hidden production dependency.

For every environment document:

- Purpose and owner
- Provisioning method
- Configuration and secret source
- Data policy
- Access policy
- Deployment path
- Monitoring and cleanup policy

## Infrastructure as code

- Provision reproducibly through version-controlled infrastructure definitions.
- Review changes through pull requests and automated plans.
- Pin providers/modules where practical.
- Store state securely with locking and restricted access.
- Detect drift and avoid untracked console changes.
- Separate reusable modules from environment-specific composition.
- Validate destructive changes and define recovery before apply.

## CI pipeline baseline

A typical pull-request pipeline includes:

1. Dependency installation from a lockfile
2. Formatting verification
3. Linting and static analysis
4. Type checking
5. Unit and integration tests
6. Secret scanning
7. Dependency and source vulnerability scanning
8. Build/package validation
9. Container and infrastructure scanning when applicable
10. Preview or ephemeral environment for high-value flows when justified

Protect deployment credentials. Untrusted pull requests must not receive production secrets.

## CD and release safety

- Produce immutable versioned artifacts once and promote them between environments.
- Record source revision, build metadata, dependencies, and deployment actor.
- Use health checks and automated post-deployment verification.
- Prefer rolling, blue/green, canary, or feature-flagged release based on risk.
- Stop or roll back when error, latency, saturation, or business guardrails regress.
- Separate database expansion from contraction for zero-downtime schema changes.
- Keep a tested rollback or forward-fix procedure.

## Containers

- Use small trusted base images and multi-stage builds.
- Run as a non-root user where possible.
- Do not bake secrets into layers or images.
- Define CPU/memory requests and limits based on measurements.
- Include a health check appropriate to the platform.
- Write logs to standard output/error unless platform standards differ.
- Scan images and rebuild when base-image vulnerabilities are fixed.
- Use a read-only filesystem and drop unnecessary capabilities when feasible.

## Service reliability

For each service define:

- Service owner and support channel
- Service-level indicators and objectives
- Error-budget policy
- Dependencies and critical paths
- Capacity assumptions
- Failure modes and degraded behavior
- Runbooks and escalation
- Backup and recovery objectives

Golden signals:

- Traffic
- Errors
- Latency
- Saturation

Also monitor business outcomes and data-pipeline freshness where applicable.

## Logging, metrics, and tracing

- Use structured logs with timestamp, severity, service, environment, and correlation identifiers.
- Redact secrets and sensitive personal information.
- Emit metrics that are bounded in cardinality.
- Trace important cross-service operations and external dependencies.
- Tie dashboards and alerts to user impact and service objectives.
- Every paging alert should be actionable, owned, and linked to a runbook.

## Backup and disaster recovery

Define for each data store:

- Recovery point objective
- Recovery time objective
- Backup frequency and retention
- Encryption and access controls
- Cross-zone/region/account strategy where required
- Restoration steps and dependencies
- Test schedule and evidence

A backup is not proven until restoration is tested.

## Incident response workflow

1. Declare ownership and severity.
2. Stabilize the service and reduce blast radius.
3. Communicate impact and updates through approved channels.
4. Preserve logs, events, and a timeline.
5. Recover through rollback, failover, capacity change, or feature disablement.
6. Verify user-facing recovery.
7. Complete a blameless root-cause analysis.
8. Assign preventive actions with owners and dates.

## Production change checklist

```text
Change summary:
Risk and blast radius:
Dependencies:
Pre-change checks:
Backup or recovery point:
Deployment steps:
Verification signals:
Abort conditions:
Rollback steps:
Owner and communication channel:
```

## Cost awareness

Track major cost drivers such as compute, managed databases, egress, storage, observability, queues, model inference, and third-party APIs. Optimize unit economics and waste only after preserving reliability and security requirements.
