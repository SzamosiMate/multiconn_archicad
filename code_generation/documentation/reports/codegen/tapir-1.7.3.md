# Tapir 1.7.3 codegen record

**Input:** two documentation JavaScript files from upstream tag 1.7.3, fetched 2026-10-26, updating 1.7.2. **Baseline:** `6257d20` (`origin/main` at that run); tracked outputs initially matched it. No implementation-source review was part of generation.

Adds 112 commands and removes none. Thirteen command schemas change directly, with additional changes through shared types. Common types gain 157 definitions and change 59; command models gain 204 and change 11. These are public-definition counts, not distinct expanded wire contracts. Four Unified API methods have compatibility consequences.

## Patch decisions by reason

Two Permanent operations extend the established MEP modification-item naming list. Add 161 Temporary operations, retire two, and keep retained classifications unchanged. Historical final inventory: **82 Permanent + 241 Temporary** expanded operations, counting loop iterations separately; compatibility aliases are separate.

### Temporary

Name conditional database selectors without flattening their alternatives; preserve `DetailsOfElement` after success-union nesting changes; separate preference/opening read, default and partial-update contracts; give contextual names to enums, request items, success branches and nested geometry/ancestry. Share only equivalent object roles, read/write enums, repeated formats and constrained project-data names. Keep enum identity, requiredness, bounds, descriptions and error alternatives intact.

Retirement requires equivalent named contracts/references in released documentation at every affected consumer. Source merges and release tags alone are insufficient; preserve old imports with compatibility aliases when names differ. The [active queue](../../schema-patch-tracking.md) owns ongoing source/PR state and deferred dependencies. Full historical calls/consumer paths remain at `776808e:code_generation/documentation/reports/codegen/tapir-1.7.3.md` in Git.

### Removed patches

Retire graphic-rule readback extraction in favor of released `GraphicOverrideRule`, retaining `GraphicOverrideRuleDetails` as an alias. Retire marker-parameter item extraction in favor of `StoredGDLParameter`, retaining `MarkerGDLParameterDetails` and its established `Flag` enum identity. The marker adoption also relaxes `value` requiredness; it is not an identical-requiredness claim.

## Compatibility and generator decisions

`change_window` uses concrete `DatabaseByWindowType`/`DatabaseById` branches of the former model name. `get_design_option_sets` returns a result wrapper instead of an unwrapped list. Element-detail reads include error entries and stricter reported curtain-wall/drawing/reveal fields. Inner property-value errors use `PropertyValueErrorItem`; outer element errors retain `ErrorItem`.

Allow valid JSON wire keys such as `2d`/`3d` while retaining Python definition-name and syntax checks; aliases and functional TypedDicts own representation. Add `PropertyValueErrorItem` to batch-results error containers so inner failures are not sent to successful-value accessors. These are generator/runtime concerns, separate from schema patch classifications.

The run records 80 retained and 161 new Temporary operations for upstream follow-up. Later submissions/deferred references are maintained in [active tracking](../../schema-patch-tracking.md) and the separate upstream-refinement records. No pending generation or patch-classification decision was recorded.
