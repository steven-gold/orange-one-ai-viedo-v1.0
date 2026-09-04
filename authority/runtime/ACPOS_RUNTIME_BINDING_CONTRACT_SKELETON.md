# ACPOS Runtime Binding Contract Skeleton

Revision: 2026-09-04 POST-MIGRATION
Status: CONTRACT_ONLY_NOT_PRODUCTION_BOUND

## Purpose

Define the minimum contract boundary required before production runtime binding.
This file does not implement database adapters, providers, APIs, or business runtime behavior.

## Lifecycle Contract

Runtime lifecycle stages:

1. DISCOVER
2. VALIDATE_CONFIGURATION
3. INITIALIZE_ADAPTERS
4. HEALTH_CHECK
5. READY
6. FAIL_CLOSED

## Production Boundary Rules

- Controlled runtime is not production runtime.
- Test adapters must not satisfy production binding requirements.
- Missing production dependencies must fail closed.
- Runtime completion requires implementation and validation evidence.

## Adapter Contract Requirements

A production adapter must define:

- initialization entry
- dependency validation
- health/readiness response
- failure handling
- correlation_id propagation
- audit event integration

## Error Contract

Required categories:

- configuration_missing
- adapter_not_bound
- dependency_unavailable
- runtime_not_ready

## Database Binding Placeholder

Database implementation is intentionally excluded.
Required before implementation:

- approved database driver contract
- connection environment contract
- lifecycle ownership
- transaction boundary definition

## Validation Gate

This contract is complete only when:

- implementation exists
- build passes
- runtime validation passes
- production binding evidence exists
