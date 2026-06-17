# RequestTransformer immutable request transformation

## Summary

- Deep-clones `req.body`, `req.query`, `req.params`, and `req.headers` before applying request transformations.
- Stores transformed request data on `req.transformedRequest` and returns it as `TransformationResult.data`.
- Leaves the original Express request objects and any cached downstream references unchanged.
- Adds regression coverage for masking `body`, `query`, and `params` without mutating the original request surfaces.

## Why

`applyRequestTransformations()` previously reassigned `req.body`, `req.query`, and `req.params` after applying privacy transformations. Middleware that cached those references could observe masked/transformed values unexpectedly. This change makes transformed data explicit and avoids in-place mutation of Express request objects.

## Testing

- Passed: `cd backend && npm.cmd test -- RequestTransformer.test.ts`
- Blocked by pre-existing repository issues: `cd backend && npm.cmd run build`
  - Fails in unrelated files such as `src/routes/audit.ts`, `src/routes/privacy.ts`, `src/routes/hsm.ts`, and `src/services/legalRequirementsService.ts`.
- Blocked by pre-existing repository issues: `cd backend && npm.cmd test`
  - New `RequestTransformer.test.ts` passes.
  - Existing failures include unrelated route compile errors, `KeyBackupService.ts` Buffer typing, and two `DistributedCacheManager` fallback assertions.
- Blocked locally: `npm.cmd run format:check`
  - The CI workflow command only runs frontend Prettier with `|| true`.
  - On Windows `cmd`, `true` is not available, and Prettier reports unrelated existing frontend syntax errors in files such as `frontend/src/components/CollaborationInterface.tsx`, `frontend/src/components/FileUpload.tsx`, and `frontend/src/components/PerformanceCharts.tsx`.

## Notes for reviewers

Downstream middleware that needs transformed request data should read `req.transformedRequest` instead of `req.body`, `req.query`, or `req.params`.
