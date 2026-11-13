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

## Merge check

From the MultiConn checkout, pass the Tapir checkout and the already-fetched base ref. Use Python 3.12 or newer and Git with `merge-tree --write-tree` support.

```text
python .agents/skills/multiconn-upstream-patches/scripts/check_schema_merge.py --repo "<Tapir checkout>" --base upstream/main --head HEAD
```

Pass the actual fetched upstream ref or SHA if it has a different name. `--head` selects a committed proposal. Use `--scratch "<existing writable directory>"` when the system temporary directory is unavailable. The script prints the two commit IDs and synthetic merge tree. It generates both outputs with Tapir's generator and keeps the snapshots and merge objects in temporary storage. This avoids comparing stale files under `docs/archicad-addon` and leaves the checkouts and remote branches untouched.

- Exit `0` means the input and response contracts and existing shared definitions compare equal. New named definitions are allowed and their references are checked.
- Exit `1` reports structural differences by path. Review every difference, including any intended breaking correction. Match each intended change to its source evidence and report it explicitly. Do not waive a whole command when only one path was intended to change.
- Exit `2` means the check could not finish, for example because the merge conflicts, the generator fails, a JSON key is duplicated, or a reference cannot resolve. Resolve the underlying problem and rerun the check.

The comparison ignores prose annotations and handles the required-only object selectors used by Tapir. It follows references while comparing constraint siblings and recursive schemas. It checks the documentation generator's target Archicad version. Continue to review annotations, common-schema access and execution separately, and build or run live checks when the change warrants them.

### Local check and Tapir's command workflow

The proposed Tapir `schema_refinement.yml` in PR #2814 calls `tools/check_schema_refinement.py`. Its structural rules currently match this skill's check: compare current base with the proposed merge, resolve references, preserve constraints and union semantics, and reject removed commands, fields, or existing definition names. Added definitions are allowed. Both use the docs generator's newest supported Archicad version.

The local script runs each revision's own documentation generator and prints structural differences. The workflow uses a trusted default-branch generator, rejects links in snapshots, runs without write credentials, and saves a JSON report that also includes annotation differences and new names. Its command controller separately checks permissions, file scope, builds, reviews, and ref freshness. Those are not part of the local script's structural check.

Use the local script for reviewed source proposals. Where the upstream workflow is available, its result is the final check for that workflow; a local pass does not authorize merging or remove the API's remaining base race. Do not execute an unreviewed PR's Python through the local script.
