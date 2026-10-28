# Tapir 1.7.2 codegen record

**Input:** documentation schemas fetched from upstream tag 1.7.2, updating 1.7.1. **Baseline:** `8e051ec8a182116fb2153ecdc2695acc8653be12`; initial tracked outputs matched it. No implementation-source review was part of this generation run.

Adds 46 commands and removes none. There are 21 changed released command contracts plus two existing commands affected by restored cleaner constraints. Public types gain 176 names (119 release/naming models and 57 recovered aliases); 25 existing type contracts change. Unified API compatibility changes affect eight methods. Additions cover electrical systems, Graphic/Graphical overrides, grids, geometry/quantities, projection/images, MEP systems and design-option management.

## Permanent

Fifteen new operations extend established creation/connection/modification item-naming lists, covering electrical payloads, level dimensions, MEP systems/groups, curtain walls, graphic overrides and grids. Keep creation, modification and readback models distinct wherever required fields or meanings differ. This established naming-list exception does not make other schema-specific extractions permanent.

## Temporary

The historical final inventory is 82 expanded Temporary operations: 60 naming/conditional-variant operations and 22 shared references. This includes 71 new operations, nine retained hotlink/status/marker operations and two older `Hole2D`/`TextData` variant operations reclassified from Permanent.

Lasting decisions: name contextual success branches and constrained pattern scalars; keep grid read/write parameter forms and differing fitting-table rows distinct; preserve Graphic versus Graphical override contracts; share equivalent electrical settings, grid default/read details, active-combination IDs, criterion positive/negative enums and text-frame enums. Keep filtering enums separate from edit enums when values differ. Selection and operator rules described only in upstream prose are not new runtime validators.

Retire only when released equivalent definitions and references cover every consumer, preserving requiredness, bounds, union/error behavior and enum values. Preserve old imports through aliases when upstream chooses another name. The [active queue](../../schema-patch-tracking.md) owns remaining paths and retirement conditions; the full historical inventory is available at `776808e:code_generation/documentation/reports/codegen/tapir-1.7.2.md` in Git.

## Removed patches

Retire 12 operations (two Permanent, ten Temporary) supplied by the released refinements: mesh partial updates, revision custom-scheme entries, beam modification holes, wall story links, slab structure and reservation-user sharing. Destination contracts match; no alias change is needed. Historical final inventory is 80 Permanent + 82 Temporary operations. Retained baseline behavior is unchanged; no breaking/source-review patch is introduced.

## Compatibility and generator decisions

Two navigator creation/clone payloads now require destination parents. View renovation-filter identifiers use `GuidId` wrappers. MEP preference-table reads return a result wrapper with required `referenceSet`; favorite export returns an execution result. Restored alias constraints reject empty autotext keys and require four RGBA integers.

Preserve root-alias constraints as validation metadata on plain values; recover named union aliases without altering generated call behavior. Repair functional TypedDicts only for the demonstrated recursive fields. JSON property keys need not be Python identifiers. Generated test-data recursion limits must not weaken runtime schemas. Avoid cleaner/generator special cases where schema-level naming/reuse suffices.

No pending generation or classification decisions were recorded; later upstream state belongs to active tracking.
