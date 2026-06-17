# Fix API key list response mutation vulnerability

## Summary

This PR fixes a high-severity API key management issue where `APIKeyManager.listKeys()` returned shallow-copied key objects. Nested objects and arrays such as `permissions`, `restrictions`, `rateLimit`, and `metadata` remained shared with the internal `Map`, allowing callers to mutate stored API key state without going through `updateKey()` or `revokeKey()` and without audit logging.

## Changes

- Deep-clone every key returned by `listKeys()` using `structuredClone`.
- Preserve the existing `keyHash` redaction behavior after cloning.
- Normalize partial `rateLimit` inputs over default limits so created keys always match the stored `APIKey` type.
- Add a regression test proving mutations to the returned list and nested key fields do not affect stored key state or validation.
- Fix a narrow logger typing issue that prevented ts-jest from compiling mocked logger imports under strict TypeScript settings.
- Synchronize `backend/package-lock.json` with `backend/package.json` so `backend/npm ci` can install dependencies.

## Security Impact

Callers can no longer use `listKeys()` results to:

- Add permissions such as `admin` to stored keys.
- Deactivate or reactivate keys by mutating `metadata.isActive`.
- Alter IP, origin, or service restrictions.
- Change stored rate limits.

All persistent key changes must continue through the intended manager methods.

## Verification

- PASS: `cd backend && npm.cmd ci`
- PASS: `cd backend && npm.cmd test -- APIKeyManager.test.ts --runInBand`

## Known Existing Blockers

- `cd backend && npm.cmd test -- --runInBand` still fails in unrelated suites:
  - `DistributedCacheManager.test.ts` has failing fallback expectation tests.
  - Several route files contain pre-existing malformed imports/syntax, including `src/routes/auth.ts`, `src/routes/privacy.ts`, and related route/build errors.
- `cd backend && npm.cmd run build` is blocked by the same pre-existing route syntax/type errors.
- Root `npm.cmd run format:check` is blocked on Windows because the script uses `|| true`; before that shell issue, Prettier reports existing frontend syntax errors unrelated to this backend security fix.
