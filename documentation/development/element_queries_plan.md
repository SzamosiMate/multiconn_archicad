# Element query development plan

Updated 2026-11-12, Europe/Budapest.

Current behavior belongs in the [guide](../utilities/element_queries.md),
[reference](../utilities/element_query_reference.md), and
[editor integration guide](../utilities/element_query_editing.md). This page
records remaining work, agreed constraints, and evidence behind decisions.
Backlog entries do not authorize implementing the entire backlog.

The consumer owns NiceGUI controls, bindings, previews, and selection behavior.
Its [widget plan](../../../TSPC-python-scripts/ai%20prompt/ELEMENT_QUERY_UI_PLAN.md)
lives in the sibling repository. Keep engine decisions here and link to them
from the consumer plan.

## Implemented

- Strict executable query/test models, schema versioning, metadata validation,
  shared field discovery, batched context preparation, and predicate evaluation.
- Serializable incomplete row drafts, compilation with AND precedence and
  parentheses, expression-to-row source maps, and framework-neutral input descriptions.
- Concise and diagnostic search, plus strict and aligned supplied-ID filtering.
  Core already raises whole-command Tapir errors; no duplicate handling is needed.
- Query listing defaults to the explicit main/floor-plan database and both
  `IncludeSubElemObjects` and `IsIndependent`. General and typed listing share
  those defaults. Explicit keyword overrides replace the corresponding default.
- `get_3d_elements()` uses both flags on Tapir 1.5.3+, retaining
  `IsIndependent` alone on older versions and its existing database behavior.
- Five immutable type presets: `TYPES_ALL`, `TYPES_3D`, `TYPES_3D_COMPONENTS`,
  `TYPES_3D_WITH_COMPONENTS`, and `TYPES_2D`. Presets exclude `Unknown`, `Group`,
  `Hotlink`, and `CamSet`; individual Camera belongs to 2D. Components are explicit
  stair/railing/curtain-wall parts and beam/column segments, independently of filters.
- Presets appear before individual types in element-type input descriptions,
  using Archicad's All Types / 3D Types / 2D Types labels and matching component names.
  They save concrete types. The executable schema still accepts custom combinations.
- Query documentation separates practical use, reference contracts, editor
  integration, and this development plan.

The earlier listing-return concern was withdrawn: core already raises a
top-level Tapir command error before generated response parsing. Broad generator
annotation changes were reverted and remain outside this branch.

## Release boundary

The agreed first-release search scope is **floor plan only**. It remains the
default after future database predicates are added, so existing queries retain
their meaning. No database picker or predicate is required for this release.

The engine implementation includes listing/database defaults, type presets and
the focused Tapir 2.0.0 SI property-read backport below. Angles deliberately use
degrees. Do not add locale parsing or implicit floating-point tolerances.

Before release, review the resulting documentation and package the agreed scope.
Do not turn optional extension ideas below into release requirements. The widget
must separately define selection behavior when the active window differs from
the query's floor-plan scope.

## Canonical numeric property reads

Implemented as a focused backport from `origin/update-to-tapir-2.0.0` (`e7be637`),
without adopting the rest of that branch. Only the read command's parameter
models, method and matching schema/tests are brought across; response shapes
are unchanged. The optional flag defaults to omission, preserving existing
payloads on older Tapir. This intentionally differs from the update branch's
explicit `False` client default.

`PropertyUtilities.get_property_values_per_element_result()` and its raw helper
accept keyword-only `use_si_units=False`. Query sources explicitly request
`True` alongside availability; ordinary utility callers keep display strings.
Explicit SI reads reject Tapir versions below 2.0.0 rather than falling back to
localized strings. The evaluator never replaces decimal commas.

The API supplies precise locale-independent numeric strings in SI units,
**except degrees for angles**, confirmed as the intended operand contract on
2026-11-13. Reads preserve row/cell errors and the original string precision.
Numeric comparisons remain exact; choosing explicit comparison tolerances is
separate from canonical value retrieval.

The temporary `backport_property_si_units()` schema patch preserves this field
when regenerating the pinned 1.8 client. Remove it and its call when merging the
2.0.0 schema, retaining omission for existing callers. See the
[active backport record](../../code_generation/documentation/schema-patch-tracking.md#si-property-read-backport--2026-11-13).

Diagnostic evidence: in `test_kész`, Archicad 27 / Tapir 2.0.0, each of four
built-in Height fields returned 157 available values out of 171 candidates.
Examples were `"3,00"`, `"0,15"`, and `"2,13"`; 14 reads were unavailable.
The current `float()` conversion fails for comma decimals, and concise search
omits those errors, explaining zero matches for both `is 0` and `is not 0`.
Repeat this read-only check after integration: if population/values are unchanged,
expect zero `is 0` matches and 157 `is not 0` matches.

## Database predicates and candidate scope

Agreed future direction: represent database membership as a predicate and
generalize `candidate_types()` to `candidate_scope()`, returning safe bounds for
both element types and resolved database IDs. A separate mandatory Search in
setting is unnecessary.

- AND intersects bounds; OR unions them. An unrestricted alternative makes that
  dimension unrestricted; an empty bound means no candidates. Evaluate the full
  original tree after collection, even if bounds collect extra candidates.
- Retain database membership/provenance alongside deduplicated element GUIDs.
  Resolve symbolic choices and navigator groups once per execution.
- Omitted database conditions mean Main/floor plan. In
  `(Worksheet A AND Fill) OR Wall`, collect fills from Worksheet A and walls
  from Main. Replacing only the final unrestricted bound with Main would lose
  Worksheet A; defaults need branch-aware handling.
- Mixed-branch/default handling is deferred until after the first release.
  Preserve existing floor-plan query semantics when adding it.

Required use cases:

- Fills from three selected worksheets.
- Drawing elements linked to views under View Map folder `FO`, whose source-view
  names do not contain `FO`. This is not a Layout Book subset condition. Drawing
  placement database, linked source view, folder membership, and view name are
  separate relationships; a saved view is not a unique element database.

Before exposing named-database behavior, compare typed and untyped listing in a
populated section/elevation. Tapir can replace generated elements with model-owner
GUIDs after typed filtering, so narrowing can omit a valid owner. One untyped
listing followed by normal evaluation is a proposed baseline to investigate.
Earlier checks covered explicit floor-plan listing from an Archicad 28 3D window
and named layouts on Archicad 26/28. Later Text studies do not settle the
section/elevation owner/type question.

## Listing-filter evidence

The default uses both flags because they perform different work:
`IncludeSubElemObjects` disables Tapir's automatic owned-Object postcheck;
`IsIndependent` applies the native Archicad filter during listing. Inclusion
does not override independence. The combined path avoids an expensive postcheck
while retaining native exclusions.

The flag first appears in Tapir **1.5.3**, confirmed by the
[release notes](https://github.com/ENZYME-APD/tapir-archicad-automation/releases/tag/1.5.3)
and [PR #419](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/419),
with source comparison against 1.5.2. The query engine itself requires 2.0.0;
the older-version distinction is for `get_3d_elements()`.

Read-only studies used Archicad 27 / Tapir 2.0.0 and compared complete GUID sets:

- `test_kész`: general listing returned the same 205 IDs with no flags,
  independence alone, and both flags. Inclusion alone returned 298; all 93 extras
  were Objects. Normal Text `htd`, eight associated Labels, and a Dimension
  survived independence. Another 19 databases yielded the same 883 Text IDs.
- A Terra subagent repeated the study in the real teamwork project
  `EVE_DD_AR_MU-LO`, Archicad 27 build 6000, port 19723. Text (971), Label (4,973),
  Dimension (4,490), ColumnSegment (1,031), BeamSegment (1,087), and
  CurtainWallPanel (1,171) had identical sets with no flags and independence.

| Object-listing flags in the real project | Objects | Observed time |
| --- | ---: | ---: |
| None | 47,441 | 35.11 s |
| IsIndependent | 47,441 | 34.84 s |
| IncludeSubElemObjects | 67,819 | 1.16 s |
| Both | 47,441 | 0.79 s |

All three 47,441-Object sets were equal. Inclusion alone added 20,378 IDs and
removed none. These are single-run measurements, not controlled benchmarks or
guaranteed speedups. The full default general listing timed out after 50 seconds
in the real project, so no complete general-listing equivalence was established.

That study also sampled Text in 19 of 558 other databases across all seven
available categories: section, elevation, interior elevation, worksheet,
3D document, layout, master layout. Its 102 Text occurrences had equal sets and
successful listing statuses. It was not exhaustive.

Limits and interpretation:

- Normal texts `Nyílászáró / Opening` and `20 m`, and associated Object/Railing
  property labels, remained. Association alone does not remove a Label.
- No concrete extra Text exclusion was demonstrated. Label text and dimension
  notes are not evidence of separately enumerable Text elements. Do not present
  the earlier speculative annotation-text example as a finding.
- Native independence is not a general component filter. The tested explicit
  segments/panels survived; Treads and Risers were not verified live.
- Equal sets do not prove universal equivalence between the native filter and
  Tapir's custom Object check across projects/versions.
- `FilterElements` applies native flags without the listing postcheck. In the
  small project, independence rejected all 93 dependent Objects. Inclusion is a
  listing switch, so it cannot undo independence in a per-element filter.
- Main-3D type membership and IFC-export eligibility are separate questions.

Sources: [Tapir 2.0.0 element commands](https://github.com/ENZYME-APD/tapir-archicad-automation/blob/2.0.0/archicad-addon/Sources/ElementCommands.cpp),
[native filter documentation](https://archicadapi.graphisoft.com/documentation/acapi_element_filter),
[Text](https://archicadapi.graphisoft.com/documentation/api_texttype),
[Label](https://graphisoft.github.io/archicad-api-devkit/struct_a_p_i___label_type.html),
and [dimension-note](https://graphisoft.github.io/archicad-api-devkit/struct_a_p_i___note_type.html) structures.

## Deferred criteria

| Idea | Next investigation / constraint |
| --- | --- |
| Filter predicates | Optional, low priority; no current implementation plan. Preserve defaults for queries without them. Collect conservative candidates across OR branches; distinguish scope-expanding listing switches from native element tests. |
| Inside marquee | Later addition, not needed for release. Decide containment versus intersection, database/view/story context, no-marquee behavior, and supported API feasibility. Keep candidate collection conservative. |
| Layer / layer combination | Reuse attribute identities and test supplied candidates. A combination criterion concerns visible layers; do not inherit the main-3D convenience utility's population restriction. |
| IFC IDs / type | Check existing built-in property fields before adding a family. Duplicate labels need verification; exact type reads exist, descendant matching needs hierarchy metadata. |
| IFC Type Product / assignment | Distinguish returned type class from Archicad's Type Product criterion. SDK assignment trees from Archicad 28 need a suitable Tapir integration. |
| GDL / arbitrary IFC properties | Per-element reads exist; project-wide discovery needs investigation. SDK library-part/default-parameter metadata may help GDL. |
| Other named criteria | Check Home Story, Renovation Status, Design Option, and Hotlink Source against existing discovery first. |

## Verification

For future changes, run the relevant offline examples and utility unit tests;
editor changes also need consumer/headless verification. Test version boundaries,
default versus explicit listing options, both listing paths, errors, empty inputs,
and duplicate alignment when affected. Live investigations should be read-only
and record project, Archicad/Tapir version, complete GUID differences, and limits.
An optional extension pilot should verify that another supported test family
gains discovery, input descriptions, serialization, and construction without a
new draft class; coordinate renderer checks with the consumer separately.

Implementation lives in `src/multiconn_archicad/utilities/queries/`, bound
namespaces in `utilities/namespaces/`, and search results in
`utilities/results/query_results.py`. Keep unrelated client-generation and
documentation refactors outside this branch.
