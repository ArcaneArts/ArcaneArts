# Parity Checklist

Every migration must preserve 1:1 behavior. If any item cannot be satisfied, stop and keep the stage for review.

## Required Parity Areas

- App shell and top-level bootstrap
- Route graph and page entrypoints
- Hooks, state lifecycle, and event wiring
- Service, repository, and connection behavior
- Async flows, loading states, and error states
- Forms, validation, and field semantics
- Asset loading and static content structure
- Theme, stylesheet, and visual mode behavior
- Local package boundaries and path wiring

## Hard Failure Conditions

- Missing 1:1 route or navigation parity
- Missing 1:1 component or widget parity
- Hooks or state lifecycle cannot be preserved
- Service or auth flows cannot be preserved
- Required local package is not eligible for direct migration
- Target template shape would need wrappers or compatibility shims
- Destination would need to be mutated before parity passes

## Audit Gate

Promotion is allowed only when:

- the parity audit reports zero blockers
- the manual parity checklist is fully checked
- required staged packages exist and are rewired
- the staged target still matches its selected Oracular template family
