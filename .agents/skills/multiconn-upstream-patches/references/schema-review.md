# Semantic schema review

## Sharing and naming

Sharing is semantic, not just shape matching. `Zoom` and drawing bounds can have identical coordinates but represent different concepts. A beam-hole modification payload without `holeId` differs from the identified read model; preserve its positive width/height constraints and conditional height meaning.

Use singular scalar enum names and domain-specific names for narrow concepts: `MEPDomain`, `RoofLevel`, `RoofPivotLine`. Search existing definitions. Report client compatibility alias needs for release adoption; do not edit generated models during upstream work.

Inspect SDK contracts precisely. A direct `Domain` return differs from `Result<Domain>`, which can carry an error. An `Unknown` switch default is not proof of a fourth SDK enum value or a reachable normal result. An explicit error-to-string fallback is part of Tapir's output handling. An Equipment element can lack a domain while its individual ports have domains; do not tighten an empty-string element response based on a port getter.

## Descriptions

- Move generic descriptions about the extracted concept to the shared definition.
- Keep meaningful caller defaults, restrictions and operation effects at the referencing property. Split generic/contextual text when needed.
- Remove redundancy but retain distinct facts. Do not mechanically duplicate descriptions.

Inspect the actual target-branch renderer. A valid sibling description can be swallowed when the renderer replaces the whole reference node. If both descriptions are supported, check that resolving a caller does not mutate the shared definition or leak context to another caller. If support is absent, keep necessary context in a rendered location or identify the separate renderer dependency before moving it.

Keep real limitations and supported-version facts; remove investigation narratives and repeated justifications from API prose. Never shorten away a default or restriction. Report full quoted strings for every retained double-description case, with its command/property.

## Compatibility and evidence

Distinguish command wire behavior, schema acceptance, generated public API and published documentation. Extraction can rename a client type; enum tightening can reject input before execution; fixing `#ref` restores a previously ineffective constraint. Do not describe all of these as “no behavior change.”

Use released unpatched schemas as evidence for current client input, and interpreted current source for proposed upstream contracts. Normalize Tapir `#/Name` references to MultiConn `#/$defs/Name` for comparison, preserving siblings and annotations. A generic expander does not necessarily reproduce Archicad or renderer behavior.

Preserve `oneOf` versus `anyOf`, GUID-only versus error-union identifiers, and required versus optional variants. Similar generated Python is insufficient proof of equivalent schemas.
