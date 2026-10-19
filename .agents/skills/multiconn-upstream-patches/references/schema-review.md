# Semantic schema review

## Sharing and naming

Sharing is semantic, not just shape matching. `Zoom` and drawing bounds can have identical coordinates but represent different concepts. A beam-hole modification payload without `holeId` differs from the identified read model; preserve its positive width/height constraints and conditional height meaning.

Use singular scalar enum names and domain-specific names for narrow concepts: `MEPDomain`, `RoofLevel`, `RoofPivotLine`. Search existing definitions. Report client compatibility alias needs for release adoption; do not edit generated models during upstream work.

Inspect SDK contracts precisely. A direct `Domain` return differs from `Result<Domain>`, which can carry an error. An `Unknown` switch default is not proof of a fourth SDK enum value or a reachable normal result. An explicit error-to-string fallback is part of Tapir's output handling. An Equipment element can lack a domain while its individual ports have domains; do not tighten an empty-string element response based on a port getter.

## Descriptions

- Put general object meaning on the shared definition, and general field behavior on that field. A creation-time flag's meaning belongs on the shared flag, not repeated on all enclosing object references.
- Keep only unique caller defaults, restrictions, effects, field-name mappings or readback expectations at referencing properties. If there is nothing distinct to add, use a plain reference.
- Split generic and contextual facts rather than copying whole descriptions. Preserve real limitations and supported-version facts; remove redundant explanations and investigation narratives. Never shorten away a default or restriction.

Inspect the actual target-branch renderer. A sibling description can be swallowed when the renderer replaces the whole reference node. Where both descriptions are supported, verify that resolving a caller does not mutate the definition or leak context to another caller. Otherwise keep necessary facts in a rendered location or identify the renderer dependency. Record full strings/locations for retained double-description cases in the single run report.

## Compatibility and evidence

Distinguish command wire behavior, schema acceptance, generated public API and published documentation. Extraction can rename a client type; enum tightening can reject input before execution; fixing `#ref` restores a previously ineffective constraint. Do not describe all of these as “no behavior change.”

Use released unpatched schemas as evidence for current client input, and interpreted current source for proposed upstream contracts. Normalize Tapir `#/Name` references to MultiConn `#/$defs/Name` for comparison, preserving siblings and annotations. A generic expander does not necessarily reproduce Archicad or renderer behavior.

Preserve `oneOf` versus `anyOf`, GUID-only versus error-union identifiers, and required versus optional variants. Similar generated Python is insufficient proof of equivalent schemas.
