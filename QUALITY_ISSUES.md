# Standard Quality Issues

This document contains 15 standardized quality issues for Stellar Privacy Analytics. Each issue follows the same structure: issue ID, issue title, issue type, severity, priority, affected component, labels, detailed description, preconditions, steps to reproduce, expected behavior, actual error or observed behavior, acceptance criteria, and verification notes.

---

## QI-001: Missing Validation for Differential Privacy Epsilon

**Issue Title:** Missing Validation for Differential Privacy Epsilon  
**Issue ID:** QI-001  
**Issue Type:** Quality / Privacy Security  
**Severity:** High  
**Priority:** High  
**Affected Component:** Backend differential privacy utilities  
**Labels:** `privacy/security`, `component/backend`, `priority/high`

### Detailed Description

The privacy query engine accepts differential privacy epsilon values without consistent validation. Epsilon is a core privacy parameter because it controls the privacy-utility tradeoff for differential privacy noise. If the value is zero, negative, non-numeric, or extremely large, the system may generate invalid noise, produce misleading analytics, or weaken privacy guarantees. The current behavior may allow requests to continue into the noise generation pipeline before the value is rejected, or it may fail with an internal error that does not clearly explain the invalid parameter.

The expected standard is that all privacy-enabled queries validate epsilon before any query execution or noise generation occurs. Invalid values should be rejected with a clear HTTP `400 Bad Request` response and a structured error message. Valid values should continue through the normal privacy pipeline without additional ambiguity.

### Preconditions

- Backend service is running.
- Privacy query endpoint is available.
- Caller can submit analytics queries with privacy parameters.

### Steps to Reproduce

1. Send an analytics request with `epsilon` set to `0`.
2. Send an analytics request with `epsilon` set to `-0.5`.
3. Send an analytics request with `epsilon` set to `1000000`.
4. Send an analytics request with `epsilon` set to `abc`.
5. Observe validation behavior and response status.

### Expected Behavior

- The API rejects invalid epsilon values before noise generation.
- The response returns HTTP `400 Bad Request`.
- The error message clearly identifies the invalid parameter.
- No analytics result is returned when epsilon is invalid.

### Error / Observed Behavior

```text
Error: Invalid epsilon value. Expected a positive finite number within the configured privacy bounds.
```

Observed behavior: The request may proceed without validation, produce misleading analytics, or fail with an unhelpful internal error.

### Acceptance Criteria

- [ ] Epsilon must be required for privacy-enabled queries.
- [ ] Epsilon must be a positive finite number.
- [ ] Epsilon must be within configured minimum and maximum bounds.
- [ ] Invalid values return HTTP `400` with a structured error response.
- [ ] Valid values continue through the normal privacy pipeline.
- [ ] Unit tests cover zero, negative, non-numeric, too small, too large, and valid values.

### Verification Notes

Verify with backend unit tests and API-level tests against the privacy query endpoint.

---

## QI-002: Privacy Budget Exhaustion Not Enforced Consistently

**Issue Title:** Privacy Budget Exhaustion Not Enforced Consistently  
**Issue ID:** QI-002  
**Issue Type:** Quality / Privacy Security  
**Severity:** Critical  
**Priority:** Critical  
**Affected Component:** Privacy budget manager  
**Labels:** `privacy/security`, `privacy/compliance`, `component/backend`, `priority/critical`

### Detailed Description

Privacy budget checks are not consistently enforced before query execution. A privacy budget defines how much privacy loss is allowed for a user, dataset, organization, or query scope. If the budget is exhausted but queries continue to execute, the platform may exceed its promised privacy protection and create compliance exposure.

This issue is critical because it can invalidate the privacy guarantees that the product advertises. The expected standard is that every privacy query checks the remaining budget before execution, rejects exhausted scopes, and updates budget state in a way that prevents overspending under concurrent requests.

### Preconditions

- Privacy budget is configured for the test user or dataset.
- Backend can process privacy analytics queries.
- The budget limit is set to a known small value.

### Steps to Reproduce

1. Configure a privacy budget limit of `1.0`.
2. Submit a query with `epsilon=0.6`.
3. Submit a second query with `epsilon=0.6`.
4. Submit a third query with `epsilon=0.6`.
5. Observe whether the second and third queries are blocked.

### Expected Behavior

- The first query succeeds.
- The second query succeeds only if remaining budget is sufficient.
- The third query is rejected once the budget is exhausted.
- Rejected responses return HTTP `429` or a privacy-specific budget error.
- Budget state is updated consistently.

### Error / Observed Behavior

```text
Error: Privacy budget exhausted. No further privacy queries are allowed for this scope.
```

Observed behavior: Queries may continue after the budget is exhausted.

### Acceptance Criteria

- [ ] Budget is checked before executing a privacy query.
- [ ] Budget is decremented only after validation succeeds.
- [ ] Budget exhaustion blocks query execution.
- [ ] Budget state is persisted or shared consistently across workers.
- [ ] Error response includes remaining budget when safe.
- [ ] Concurrent requests cannot overspend the budget.

### Verification Notes

Verify with unit tests, concurrency tests, and integration tests using a shared Redis-backed budget store.

---

## QI-003: Audit Logs Missing Required Privacy Event Fields

**Issue Title:** Audit Logs Missing Required Privacy Event Fields  
**Issue ID:** QI-003  
**Issue Type:** Quality / Compliance  
**Severity:** High  
**Priority:** High  
**Affected Component:** Audit logging service  
**Labels:** `privacy/compliance`, `component/backend`, `priority/high`

### Detailed Description

Audit logs do not consistently include required fields for privacy-sensitive actions. In a privacy analytics platform, audit logs are a primary control for accountability, incident investigation, and compliance evidence. If logs are missing actor identity, action type, resource scope, result status, timestamp, or correlation ID, it becomes difficult to reconstruct what happened and who performed an action.

The expected standard is that every privacy-sensitive operation emits a structured audit event with a complete and consistent field set. The logs must be detailed enough for compliance review but must not expose sensitive payload data, raw keys, or private identifiers.

### Preconditions

- Audit logging is enabled.
- Backend can process privacy queries and compliance workflow actions.

### Steps to Reproduce

1. Submit a privacy analytics query.
2. Trigger a compliance approval or rejection action.
3. Trigger an API key creation or revocation action.
4. Retrieve audit logs from the configured logging sink.
5. Inspect each log entry for required fields.

### Expected Behavior

Each privacy-sensitive audit log includes:

- Actor identifier.
- Action name.
- Resource identifier.
- Resource type.
- Result status.
- Timestamp.
- Correlation ID.
- Source IP or service identity.
- Failure reason when applicable.

### Error / Observed Behavior

```text
Error: Audit event is missing required fields: actorId, action, resourceId, correlationId.
```

Observed behavior: Some audit events are partial or inconsistent.

### Acceptance Criteria

- [ ] All privacy-sensitive actions emit audit events.
- [ ] Audit events include the required field set.
- [ ] Failed actions emit failure audit events.
- [ ] Correlation IDs are propagated across request handlers.
- [ ] Audit logging failures do not expose sensitive payload data.
- [ ] Tests verify required fields for query, approval, rejection, API key, and budget events.

### Verification Notes

Verify by inspecting structured logs and adding unit tests for audit event creation.

---

## QI-004: API Key Manager Accepts Expired or Revoked Keys

**Issue Title:** API Key Manager Accepts Expired or Revoked Keys  
**Issue ID:** QI-004  
**Issue Type:** Quality / Security  
**Severity:** Critical  
**Priority:** Critical  
**Affected Component:** API key manager and gateway  
**Labels:** `privacy/security`, `component/backend`, `priority/critical`

### Detailed Description

Expired or revoked API keys may still be accepted by the gateway. API keys are used to authorize access to analytics APIs, so accepting an expired or revoked key can allow unauthorized access to sensitive analytics data or administrative actions. This can happen when key state is cached, lookup logic does not check expiration, or revocation does not invalidate cached authentication results.

The expected standard is that authentication always checks the current key state before authorizing a request. Expired, revoked, missing, and invalid keys must be rejected with HTTP `401 Unauthorized`, and failed authentication attempts must be audited without exposing the key value.

### Preconditions

- Backend gateway is running.
- API key authentication middleware is enabled.
- A valid API key exists.

### Steps to Reproduce

1. Create an API key.
2. Confirm the key can access an analytics endpoint.
3. Revoke or expire the API key.
4. Send another request using the same key.
5. Observe authentication result.

### Expected Behavior

- Revoked or expired keys are rejected.
- The response returns HTTP `401 Unauthorized`.
- The key is not used to authorize the request.
- The failed authentication attempt is logged.

### Error / Observed Behavior

```text
Error: API key is expired or revoked.
```

Observed behavior: The gateway may accept the key if cache or lookup logic is stale.

### Acceptance Criteria

- [ ] Expired keys are rejected.
- [ ] Revoked keys are rejected.
- [ ] Missing keys return HTTP `401`.
- [ ] Invalid keys return HTTP `401`.
- [ ] Authentication failure is audited without logging the key value.
- [ ] Cache invalidation occurs when a key is revoked.
- [ ] Unit tests cover expired, revoked, missing, and invalid keys.

### Verification Notes

Verify with API gateway tests and audit log checks.

---

## QI-005: PII Masking Does Not Cover Nested Data Structures

**Issue Title:** PII Masking Does Not Cover Nested Data Structures  
**Issue ID:** QI-005  
**Issue Type:** Quality / Privacy Security  
**Severity:** High  
**Priority:** High  
**Affected Component:** Data anonymization and PII masking  
**Labels:** `privacy/security`, `component/backend`, `priority/high`

### Detailed Description

PII masking rules may only apply to top-level fields, leaving personally identifiable information exposed in nested arrays or objects. Analytics payloads often contain nested structures such as user profiles, account details, event metadata, and address objects. If masking is shallow, sensitive values like email addresses, phone numbers, names, or identifiers can remain visible in downstream analytics outputs.

The expected standard is recursive masking across all supported data structures. The anonymization service must process nested objects, arrays, and mixed data while preserving unrelated non-sensitive fields. Any configured PII field name or pattern must be masked regardless of its depth in the payload.

### Preconditions

- Data anonymization service is available.
- Test dataset contains nested PII fields.

### Steps to Reproduce

1. Prepare a record with nested PII fields, such as `user.profile.email`.
2. Send the record through the anonymization service.
3. Inspect the output record.
4. Repeat with arrays containing PII objects.

### Expected Behavior

- All configured PII fields are masked recursively.
- Nested objects and arrays are processed.
- Output does not contain raw email, phone number, address, or other configured PII values.
- Non-PII fields remain unchanged.

### Error / Observed Behavior

```text
Error: PII field user.profile.email was not masked in nested object.
```

Observed behavior: Raw nested PII values appear in anonymized output.

### Acceptance Criteria

- [ ] Masking applies recursively to nested objects.
- [ ] Masking applies to arrays of objects.
- [ ] Configured PII field names are masked by exact and pattern rules.
- [ ] Raw PII values are not present in the anonymized output.
- [ ] Unit tests cover nested objects, arrays, mixed data, and non-PII data.
- [ ] Masking does not alter unrelated fields.

### Verification Notes

Verify with unit tests and sample payload inspection.

---

## QI-006: Redis Connection Pool Can Leak Connections

**Issue Title:** Redis Connection Pool Can Leak Connections  
**Issue ID:** QI-006  
**Issue Type:** Quality / Reliability  
**Severity:** High  
**Priority:** High  
**Affected Component:** Redis connection pool  
**Labels:** `component/backend`, `reliability`, `priority/high`

### Detailed Description

Redis connections may not be released correctly after failed operations, which can exhaust the connection pool during high load. Redis is used for cache operations, rate limiting, privacy budget tracking, and distributed coordination. If connections are held after errors or timeouts, valid requests can eventually fail even when Redis itself is healthy.

The expected standard is that every Redis operation releases its connection in both success and failure paths. The pool should expose metrics for active, idle, pending, and error states so operators can detect exhaustion early. Health checks should report degraded status when the pool cannot acquire connections.

### Preconditions

- Redis is running.
- Backend connection pool is configured with a small maximum size.
- Backend can execute Redis operations.

### Steps to Reproduce

1. Configure Redis pool maximum size to `2`.
2. Trigger repeated Redis operations that fail or time out.
3. Continue issuing valid Redis operations.
4. Monitor active and idle connection counts.

### Expected Behavior

- Failed operations release connections back to the pool.
- Active connection count returns to expected levels.
- Subsequent valid operations succeed.
- Pool health endpoint reports healthy state when Redis is available.

### Error / Observed Behavior

```text
Error: Connection pool exhausted. Unable to acquire Redis connection.
```

Observed behavior: Connections remain active after failed operations.

### Acceptance Criteria

- [ ] Connections are released in both success and failure paths.
- [ ] Timeouts do not permanently consume pool slots.
- [ ] Pool exposes active, idle, pending, and error metrics.
- [ ] Health checks report pool exhaustion.
- [ ] Unit tests simulate success, timeout, and Redis error paths.
- [ ] Integration test confirms no pool exhaustion after repeated failures.

### Verification Notes

Verify with connection pool metrics and a stress test against Redis failure scenarios.

---

## QI-007: Cache Invalidation Can Create Recursive Pub/Sub Loop

**Issue Title:** Cache Invalidation Can Create Recursive Pub/Sub Loop  
**Issue ID:** QI-007  
**Issue Type:** Quality / Reliability  
**Severity:** Medium  
**Priority:** Medium  
**Affected Component:** Cache invalidation service  
**Labels:** `component/backend`, `reliability`, `priority/medium`

### Detailed Description

Cache invalidation events may be republished when received, causing recursive Pub/Sub messages and unnecessary processing. In a multi-instance backend, one instance should publish an invalidation event and other instances should apply that event locally. If every receiving instance republishes the same event, the cluster can create a message loop that increases Redis load and causes repeated invalidations.

The expected standard is origin-aware invalidation handling. Each event should include an origin identifier, and receiving instances should skip republishing events that originated from another instance. Duplicate detection should prevent repeated local invalidation for the same event.

### Preconditions

- Redis Pub/Sub is enabled.
- Multiple backend instances subscribe to the cache invalidation channel.
- Cache invalidation API is available.

### Steps to Reproduce

1. Start two backend instances.
2. Issue a cache invalidation request from instance A.
3. Observe Pub/Sub messages received by both instances.
4. Check whether instance B republishes the same invalidation event.
5. Monitor message count over time.

### Expected Behavior

- The originating instance publishes one invalidation event.
- Receiving instances apply the invalidation locally only.
- Receiving instances do not republish the same event.
- Message count remains bounded.

### Error / Observed Behavior

```text
Error: Cache invalidation event was republished by receiving instance, creating recursive messages.
```

Observed behavior: Message count grows unexpectedly after one invalidation request.

### Acceptance Criteria

- [ ] Received invalidation events are applied locally only.
- [ ] Events include an origin identifier.
- [ ] Receiving instances do not republish events from other origins.
- [ ] Duplicate event detection prevents repeated local invalidation.
- [ ] Metrics track published, received, duplicate, and skipped events.
- [ ] Tests cover single-node and multi-node invalidation flows.

### Verification Notes

Verify with multi-instance integration tests and Redis Pub/Sub message counts.

---

## QI-008: Search Index May Expose Raw Sensitive Terms

**Issue Title:** Search Index May Expose Raw Sensitive Terms  
**Issue ID:** QI-008  
**Issue Type:** Quality / Privacy Security  
**Severity:** Critical  
**Priority:** Critical  
**Affected Component:** Search index service  
**Labels:** `privacy/security`, `component/backend`, `priority/critical`

### Detailed Description

The search index may store or return raw sensitive terms from analytics payloads instead of masked or aggregated values. Search indexes often persist normalized terms for fast retrieval, which can unintentionally store sensitive values such as emails, phone numbers, user IDs, or internal identifiers. If these values are searchable or returned in results, privacy-sensitive data can leak outside the controlled analytics pipeline.

The expected standard is that sensitive fields are removed or masked before indexing and that search result projections never expose raw sensitive values. Index configuration must also prevent forbidden fields from being indexed. Failed indexing should not fall back to storing the raw payload.

### Preconditions

- Search index service is running.
- Indexing is enabled for analytics records.
- Test records contain sensitive terms.

### Steps to Reproduce

1. Index a record containing sensitive terms such as email, phone, or internal identifiers.
2. Execute a search query for those terms.
3. Inspect search results and stored index documents.
4. Check whether raw sensitive values are returned or stored.

### Expected Behavior

- Sensitive terms are masked before indexing.
- Search results do not expose raw sensitive values.
- Index documents contain only allowed searchable fields.
- Failed indexing does not store raw payload data.

### Error / Observed Behavior

```text
Error: Sensitive term was indexed or returned in raw form.
```

Observed behavior: Search results include raw PII or confidential identifiers.

### Acceptance Criteria

- [ ] Sensitive fields are removed or masked before indexing.
- [ ] Search result projection excludes raw sensitive fields.
- [ ] Index configuration does not include forbidden fields.
- [ ] Unit tests verify masking before index writes.
- [ ] Integration tests verify search results do not expose raw sensitive data.
- [ ] Audit logs capture indexing failures without raw payload data.

### Verification Notes

Verify with search index integration tests and direct index document inspection.

---

## QI-009: HSM Key Rotation Is Not Fully Audited

**Issue Title:** HSM Key Rotation Is Not Fully Audited  
**Issue ID:** QI-009  
**Issue Type:** Quality / Compliance  
**Severity:** High  
**Priority:** High  
**Affected Component:** HSM and master key manager  
**Labels:** `privacy/security`, `privacy/compliance`, `component/backend`, `priority/high`

### Detailed Description

HSM key rotation events may not produce complete audit records, making it difficult to prove key lifecycle compliance. Key rotation is a sensitive operation because it changes the cryptographic material used to protect data or secrets. If audit logs omit the actor, old key ID, new key ID, timestamp, result, or reason, the platform cannot reliably demonstrate that rotation followed policy.

The expected standard is a complete key lifecycle audit trail. Successful rotations and failed rotations must both be logged. Audit events must reference key IDs and versions without exposing raw key material.

### Preconditions

- HSM configuration is available or mocked.
- Master key manager is running.
- Key rotation endpoint or workflow is available.

### Steps to Reproduce

1. Trigger a master key rotation.
2. Confirm the new key becomes active.
3. Retrieve audit logs for the rotation event.
4. Inspect the audit record for key identifiers, actor, timestamp, and result.

### Expected Behavior

- Rotation creates a new key version.
- Old key is retired according to policy.
- Audit log records actor, old key ID, new key ID, timestamp, result, and reason.
- Failed rotation emits a failure audit event.

### Error / Observed Behavior

```text
Error: HSM key rotation audit event is missing newKeyId, oldKeyId, actorId, or result.
```

Observed behavior: Rotation occurs without complete audit metadata.

### Acceptance Criteria

- [ ] Successful rotations emit complete audit events.
- [ ] Failed rotations emit failure audit events.
- [ ] Audit events never include raw key material.
- [ ] Key IDs and versions are traceable.
- [ ] Rotation workflow is idempotent where required.
- [ ] Tests cover success, failure, and missing actor scenarios.

### Verification Notes

Verify with HSM mock tests and audit log assertions.

---

## QI-010: Compliance Workflow Allows Missing Reviewer Approval

**Issue Title:** Compliance Workflow Allows Missing Reviewer Approval  
**Issue ID:** QI-010  
**Issue Type:** Quality / Compliance  
**Severity:** Critical  
**Priority:** Critical  
**Affected Component:** Compliance workflow service  
**Labels:** `privacy/compliance`, `component/backend`, `priority/critical`

### Detailed Description

Compliance workflows may allow a record to move to approved state without a valid reviewer identity or required approval step. Approval workflows are used to enforce governance controls before sensitive data or privacy-sensitive changes are accepted. If the service allows missing, revoked, or unauthorized reviewers to approve a workflow, the approval process becomes ineffective.

The expected standard is that approval state transitions are enforced by the workflow definition. Required approvals must validate reviewer identity, reviewer status, and permissions before changing state. Invalid approvals must leave the workflow unchanged and must be audited.

### Preconditions

- Compliance workflow service is running.
- A workflow requiring approval exists.

### Steps to Reproduce

1. Create a compliance workflow requiring reviewer approval.
2. Submit an approval request without `reviewerId`.
3. Submit an approval request with a revoked reviewer account.
4. Submit an approval request for a workflow that does not require approval.
5. Observe workflow state transitions.

### Expected Behavior

- Approval requires a valid reviewer identity.
- Revoked reviewers cannot approve.
- Workflows requiring approval cannot skip the approval step.
- Invalid approvals return HTTP `400` or `403`.
- Workflow state remains unchanged on invalid approval.

### Error / Observed Behavior

```text
Error: Approval rejected. reviewerId is required for this workflow step.
```

Observed behavior: The workflow advances to approved without valid reviewer approval.

### Acceptance Criteria

- [ ] Required approval steps enforce reviewer identity.
- [ ] Revoked or inactive reviewers are rejected.
- [ ] Unauthorized reviewers cannot approve.
- [ ] Invalid approvals do not change workflow state.
- [ ] Approval and rejection events are audited.
- [ ] Tests cover missing reviewer, revoked reviewer, unauthorized reviewer, and valid approval.

### Verification Notes

Verify with service-level tests and workflow state assertions.

---

## QI-011: Rate Limiter Can Be Bypassed Using Forwarded Headers

**Issue Title:** Rate Limiter Can Be Bypassed Using Forwarded Headers  
**Issue ID:** QI-011  
**Issue Type:** Quality / Security  
**Severity:** High  
**Priority:** High  
**Affected Component:** Rate limit monitor and API gateway  
**Labels:** `privacy/security`, `component/backend`, `priority/high`

### Detailed Description

The rate limiter may trust unvalidated forwarded headers, allowing clients to bypass client-based limits by spoofing source identity. In deployments behind proxies or load balancers, client identity is often derived from headers such as `X-Forwarded-For` or `Forwarded`. If the application trusts these headers without verifying that the request came from a trusted proxy, clients can rotate header values and avoid rate limits.

The expected standard is trusted-proxy-aware client identification. Forwarded headers should be used only when the immediate peer is a trusted proxy. Otherwise, the limiter should use the direct remote address or another trusted identity source.

### Preconditions

- Rate limiting middleware is enabled.
- API gateway accepts requests with forwarded headers.

### Steps to Reproduce

1. Send repeated requests with a fixed client IP and observe rate limit behavior.
2. Send repeated requests while changing `X-Forwarded-For`.
3. Send repeated requests while changing `Forwarded`.
4. Observe whether the client can exceed the configured limit.

### Expected Behavior

- Client identity is resolved from trusted proxy configuration only.
- Spoofed forwarded headers are ignored unless from trusted proxies.
- Rate limits are enforced per real client identity.
- Bypass attempts are logged.

### Error / Observed Behavior

```text
Error: Rate limit bypass detected. Forwarded header changed client identity without trusted proxy validation.
```

Observed behavior: Client can exceed rate limits by changing forwarded headers.

### Acceptance Criteria

- [ ] Forwarded headers are ignored unless proxy is trusted.
- [ ] Rate limit key is stable for the same real client.
- [ ] Spoofed headers do not reset or bypass limits.
- [ ] Rate limit responses return HTTP `429`.
- [ ] Bypass attempts are logged without exposing sensitive data.
- [ ] Tests cover trusted and untrusted proxy scenarios.

### Verification Notes

Verify with API gateway tests using different forwarded header values.

---

## QI-012: Error Handler Returns Stack Traces to Clients

**Issue Title:** Error Handler Returns Stack Traces to Clients  
**Issue ID:** QI-012  
**Issue Type:** Quality / Security  
**Severity:** High  
**Priority:** High  
**Affected Component:** Error handling utilities  
**Labels:** `privacy/security`, `component/backend`, `priority/high`

### Detailed Description

The API error handler may return internal stack traces or implementation details to clients. Stack traces can reveal file paths, framework versions, internal routes, and implementation logic that should not be exposed outside the server. This increases the attack surface and can make debugging information available to unauthorized users.

The expected standard is a production-safe error response strategy. Validation errors may include safe field-level messages, but unexpected server errors should return a generic message to clients. Detailed errors, including stack traces, should be written only to server-side logs with a correlation ID for internal investigation.

### Preconditions

- Backend API is running.
- Error handler middleware is active.

### Steps to Reproduce

1. Trigger a known validation error.
2. Trigger a database error.
3. Trigger an unexpected exception.
4. Inspect the HTTP response body in non-production and production modes.

### Expected Behavior

- Clients receive safe, structured error responses.
- Stack traces are never returned to external clients.
- Internal errors return HTTP `500` with a generic message.
- Detailed errors are logged server-side only.
- Error responses include correlation ID.

### Error / Observed Behavior

```text
Error: API response includes stack trace or internal file path.
```

Observed behavior: Response body exposes internal exception details.

### Acceptance Criteria

- [ ] External responses do not include stack traces.
- [ ] External responses do not include internal file paths.
- [ ] Validation errors return HTTP `400` with safe field messages.
- [ ] Internal errors return HTTP `500` with generic message.
- [ ] Server logs include detailed error context.
- [ ] Tests verify production-safe error responses.

### Verification Notes

Verify with API-level tests that inspect response bodies and server logs.

---

## QI-013: Prometheus Metrics Include User Identifiers

**Issue Title:** Prometheus Metrics Include User Identifiers  
**Issue ID:** QI-013  
**Issue Type:** Quality / Privacy Security  
**Severity:** High  
**Priority:** High  
**Affected Component:** Prometheus metrics exporter  
**Labels:** `privacy/security`, `component/backend`, `priority/high`

### Detailed Description

Metrics labels may include user IDs, API keys, emails, or other sensitive identifiers, creating a privacy leakage risk. Metrics are often exposed to monitoring systems, dashboards, and multiple engineers. Labels with high-cardinality or sensitive values can leak private data and can also create performance problems in Prometheus due to label cardinality explosion.

The expected standard is safe, low-cardinality metrics labeling. Metrics may include dimensions such as route, HTTP method, status code, component, and privacy mode, but must not include user identifiers, request payloads, emails, or API keys. Automated tests should assert that sensitive values are absent from metrics output.

### Preconditions

- Prometheus metrics endpoint is enabled.
- Backend processes requests with user or API key context.

### Steps to Reproduce

1. Send requests for multiple users or API keys.
2. Scrape the Prometheus metrics endpoint.
3. Search metrics output for user IDs, emails, API keys, or request-specific identifiers.
4. Check metric labels for high-cardinality identifiers.

### Expected Behavior

- Metrics do not include user-level identifiers.
- Metrics labels are low-cardinality and safe.
- Request counts can be grouped by endpoint, status code, and privacy mode only.
- API keys are never present in metrics.

### Error / Observed Behavior

```text
Error: Prometheus metrics contain user_id, email, apiKey, or other sensitive labels.
```

Observed behavior: Metrics output includes identifiable request data.

### Acceptance Criteria

- [ ] Metrics exclude user IDs, emails, API keys, and request payloads.
- [ ] Labels are limited to safe dimensions such as route, status, method, and privacy mode.
- [ ] High-cardinality labels are rejected or sanitized.
- [ ] Metrics tests assert sensitive values are absent.
- [ ] Documentation lists approved metric labels.

### Verification Notes

Verify by scraping metrics after varied requests and adding automated tests for sensitive labels.

---

## QI-014: Dead-Letter Queue Lacks Reliable Retry and Tracking

**Issue Title:** Dead-Letter Queue Lacks Reliable Retry and Tracking  
**Issue ID:** QI-014  
**Issue Type:** Quality / Reliability  
**Severity:** Medium  
**Priority:** Medium  
**Affected Component:** Dead-letter queue and worker orchestration  
**Labels:** `component/backend`, `reliability`, `priority/medium`

### Detailed Description

Failed jobs may be added to the dead-letter queue without consistent metadata, retry policy, or status tracking, making recovery difficult. Worker failures are expected in distributed systems, but the platform must provide enough information to understand why a job failed and whether it can be retried safely. Missing metadata makes incident response slower and can cause jobs to be lost or retried incorrectly.

The expected standard is a consistent DLQ process after retry exhaustion. Each DLQ entry should include the original job ID, error message, failure timestamp, attempt count, queue name, and safe metadata. Sensitive payload data should not be copied into DLQ metadata.

### Preconditions

- Worker orchestration is running.
- A job can be forced to fail.
- Dead-letter queue is configured.

### Steps to Reproduce

1. Submit a job that fails processing.
2. Allow retries to exhaust.
3. Inspect the dead-letter queue entry.
4. Attempt to retrieve DLQ stats and job details.

### Expected Behavior

- Failed jobs are moved to DLQ after retry policy is exhausted.
- DLQ entries include original job ID, error message, failure timestamp, attempt count, and queue name.
- DLQ stats are available.
- DLQ entries can be inspected safely.
- Sensitive payload data is not exposed in DLQ metadata.

### Error / Observed Behavior

```text
Error: DLQ entry is missing originalJobId, failedAt, attempts, or error details.
```

Observed behavior: DLQ entries are incomplete or cannot be tracked reliably.

### Acceptance Criteria

- [ ] Failed jobs are moved to DLQ consistently.
- [ ] DLQ entries include required tracking metadata.
- [ ] Retry exhaustion is clearly represented.
- [ ] DLQ stats endpoint returns total, by-error, and by-hour counts.
- [ ] DLQ inspection does not expose sensitive payload data.
- [ ] Tests cover failure, retry exhaustion, stats, and metadata completeness.

### Verification Notes

Verify with worker integration tests and DLQ inspection.

---

## QI-015: Load Test Runner References Missing Worker Methods

**Issue Title:** Load Test Runner References Missing Worker Methods  
**Issue ID:** QI-015  
**Issue Type:** Quality / Test Coverage  
**Severity:** Medium  
**Priority:** Medium  
**Affected Component:** Testing utilities and worker orchestration  
**Labels:** `testing`, `component/backend`, `priority/medium`

### Detailed Description

Load testing utilities reference worker methods that are not implemented, preventing reliable load test execution and verification. Load tests are used to validate worker throughput, queue behavior, latency, and failure handling under realistic traffic. If the runner calls methods such as `getJobStatus()` that do not exist, the test fails before meaningful performance data can be collected.

The expected standard is that load test utilities only depend on implemented worker APIs, or that the required worker methods are implemented with clear behavior. The runner should report job success, job failure, latency, throughput, and clear errors when the environment is misconfigured.

### Preconditions

- Backend test suite is available.
- Load test runner is present.
- Worker orchestration code is present.

### Steps to Reproduce

1. Run the load test command.
2. Observe missing method errors.
3. Inspect worker methods referenced by the load test runner.
4. Compare referenced methods with implemented worker API.

### Expected Behavior

- Load test runner uses implemented worker methods.
- Job status can be retrieved during load tests.
- Load test runner reports success, failure, latency, and throughput.
- Missing methods are either implemented or replaced with supported APIs.

### Error / Observed Behavior

```text
Error: worker.getJobStatus is not a function.
```

Observed behavior: Load tests fail before collecting performance data.

### Acceptance Criteria

- [ ] Load test runner starts without missing method errors.
- [ ] Worker status retrieval is implemented or replaced.
- [ ] Load test reports job success and failure counts.
- [ ] Load test reports latency and throughput metrics.
- [ ] Tests or smoke checks verify the load test entry point.
- [ ] Documentation lists supported load test commands.

### Verification Notes

Verify by running the load test command in a test environment and checking that it completes or fails with a clear non-code error.
