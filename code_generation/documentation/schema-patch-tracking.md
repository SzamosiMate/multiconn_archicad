# Active Tapir schema refinements

Client release: **Tapir 1.7.1**. Last source/status check: **2026-10-18**. This file contains only open decisions and fixes awaiting released documentation. Remove an entry after confirmed release adoption; retired inventories remain in generation reports and Git history.

## Submitted following 1.7.1

**[PR #1056 — Refine API schemas following Tapir 1.7.1](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/1056)** is open. Published branch: `SzamosiMate:codex/schema-temporary-patches-1-7-1`; head `43e12ebcf55805ba7b76f1a5608c8e80112b60ed`, based on `6dfc87d54da3dbd51ebab435e5cfd05a45ffa92a`. The first ten operations are in `f1ac4d49`; the two explicitly selected older extractions are in `43e12ebc`. See the [single run report](reports/upstream-refinements-1.7.1-2026-10-17.md) for source rationale, excluded alternatives and validation limits.

Paths use the patch helpers' shorthand: property names descend through `properties`; `items` descends through array items. References use `#/$defs/` locally.

| Decision | Local operations | Original schema paths | Release-retirement condition |
| --- | ---: | --- | --- |
| Name beam modification holes and share the type enum | Temporary: 2 | `ModifyBeamsParameters/beamsWithDetails/items/holes/items`, including its `type` | Item references equivalent `BeamHoleModification`, whose `type` references `BeamHoleType`; preserve no `holeId`, positive width/height and existing required fields. |
| Reuse slab structure | Temporary: 1 | `CreateSlabsParameters/slabsData/items/structureType` | Creation field references equivalent `SlabStructureType`, retaining optionality and default/favorite rules. |
| Reuse wall story-link settings | Temporary: 3 | `CreateWallsParameters/wallsData/items/linkToSettings`; `WallDetails/linkToSettings`; `ModifyWallsParameters/wallsWithDetails/items/linkToSettings` | All three reference equivalent `LinkToSettings`, with shared field semantics and the unique placement/readback notes preserved. |
| Share Teamwork user identity | Temporary: 4 | `ReserveElementsResult/conflicts/items/user`; `GetLockableObjectSetStatusResult/conflicts/items`; `ReserveLockableObjectSetResult/conflicts/items`; `ReserveHotlinkCacheManagementResult/conflicts/items` | All four reference `User`: required numeric `userId`, string `userName`, no extra user properties; enclosing conflict wrappers unchanged. |
| Name the distinct partial mesh-update contract | Selected Permanent: 1 | `ModifyMeshesParameters/meshesData/items/meshData`, reached through local `MeshWithDetails` | Field references equivalent `MeshModificationData`; retain wrapper, optional fields, descriptions and bounds. Keep the separate wrapper extraction. |
| Name one revision custom-scheme entry | Selected Permanent: 1 | `RevisionCustomSchemeData/items` | Array references equivalent `RevisionCustomSchemeEntry`: required GUID `customSchemeKey`, string `customSchemeValue`, no extra fields. |

No new compatibility aliases are needed when the released names match these destinations. Keep current calls, categories and loud guards until `$multiconn-codegen` confirms the changes in fetched release documentation. A merged PR or release tag alone is insufficient.

No unresolved breaking source-review candidates remain. The `Hole2D`/`TextData` conditional naming helpers and other established generator workarounds remain local; their rationale is in the run report, not a separate historical inventory here.
