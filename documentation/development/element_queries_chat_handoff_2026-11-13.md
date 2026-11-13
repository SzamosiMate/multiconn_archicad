# Element queries: chat handoff — 2026-11-13

This is a self-contained handoff of the chat's work, decisions, experiments and
open questions, intended for continuing on another computer. It is a structured
record rather than a verbatim transcript of every message or tool response.
Repository-relative links are used so the document remains portable.

## Where things stand

- Repository: `SzamosiMate/multiconn_archicad`.
- Branch: **`extensible-elmement-query`** (the spelling is intentional here: this
  is the existing branch name, not a suggested rename).
- HEAD when this handoff was written: **`6111f8a` — `WIP: SI`**.
- Previous commit: **`1064007` — `test: restructured query tests`**.
- The test-suite review and the focused SI backport are committed locally.
- The live-experiment scripts and results were **untracked** when checked.
  This handoff is a newly created file as well. Commit/copy/sync those files if
  they are needed on the other computer; a normal pull of existing commits will
  not transfer untracked files.
- `.idea/` was already untracked before this work. Leave it alone.
- **Numeric comparisons still use exact floating-point equality and ordering.**
  No tolerance policy has been implemented.
- Current recommendation, after the user's coordinate-domain restriction:

  ```python
  math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10)
  ```

  This is an evidence-backed proposal, not an already implemented or explicitly
  user-approved final comparison contract.

## User's intentions and scope

1. Review the AI-authored tests for the unreleased element-query feature against
   specifications/documented behavior, reorganize and rename them accordingly,
   remove duplicated checks, and improve readability.
2. Add only the SI property-read integration before finalizing this feature branch.
   The user initially said "set", then corrected that to the **get** command.
3. Backport only the necessary `GetPropertyValuesOfElements` support from the
   separate Tapir 2.0.0 update branch, minimizing later merge conflicts.
4. Angles in **degrees** are a conscious user decision, despite SI technically
   using radians. Other measured operands use SI units.
5. Investigate floating-point behavior empirically before selecting comparison
   tolerances. The user authorized creating objects and changing the then-open
   disposable Archicad file.
6. Do not turn scientific-notation support into a release requirement. The user
   questioned whether it was promised and said covering it was not important.
7. Do not introduce a quantity/unit class merely for the comparison system.
8. Latest numerical domain: **each X, Y and Z coordinate independently lies
   between -10,000 and +10,000 metres**. No radial-distance calculation is needed.
   This supersedes the earlier discussion of a 1 km radius and excludes the
   million-metre stress fixtures from the default-tolerance recommendation.

## 1. Specification-driven test review — completed

Read the public guides/reference and compared them with the existing tests.
The original tests followed implementation layers and successive feature
iterations, with overlapping assertions and scenarios.

The reorganized query suite lives in [`../../tests/utilities/queries/`](../../tests/utilities/queries/).
It groups contracts into structure, serialization, property comparisons,
expressions, classification queries, discovery, metadata validation, execution,
search scope, results/error policies, editor fields/rows, compatibility,
registration and context preparation.

Shared fake-project and classification fixtures were extracted. Classification
query tests were separated from classification utility tests. Comparison tables
and invalid-input cases have descriptive test IDs. Tests spying on execution
context identity or internal membership-check ordering were removed in favor of
observable batching/outcome checks.

Deduplication included repeated Boolean discovery/serialization checks, manual
batch aggregation duplicating real predicate-group tests, overlapping collection
compatibility tests, and repeated command/transport propagation scenarios.
Distinct boundary tests were retained even when they share a logical scenario.

Added missing coverage included:

- Empty and explicit `None` listing overrides.
- Explicit component types under default listing filters.
- A failed database listing alongside a successful listing.
- All frozen executable model families.
- Strict-filter success, preserving duplicate matching inputs.
- Mutable draft assignment validation, incomplete/unbalanced persistence, and
  metadata-issue mapping to a source row.
- A **deeper descendant** classification case: earlier tests distinguished a
  selected item from an immediate child but did not prove that direct-child
  matching excludes deeper descendants.

Removed the test wording/assertion implying canonical SI reads before they had
actually been integrated. The later backport now supplies that integration.

Validation recorded during the review:

- Original utility suite: **611 passed**.
- Final reviewed utility suite before SI integration: **673 passed**.
- Broader selected unit checks: **877 passed** across utilities, orchestration
  unit tests, code generation and release helpers.
- Compared original and revised utility tests against the same query-engine
  source: both covered **1,186 / 1,213 statements, 97.8%**, with **no previously
  covered query-engine lines lost**.
- Ruff and whitespace checks passed.

Windows sandbox temporary-directory permissions caused unrelated release/codegen
test failures on the first broad run. The same checks passed with host permissions.
The existing `.pytest_cache` directory also produced permission warnings; commands
used `-p no:cacheprovider`.

An initial review-map README was discussed/created during the chat, but it is not
present in the current checkout. Use the actual test modules and this handoff;
do not assume that README exists.

## 2. SI read backport — implemented, HEAD `6111f8a`

Source inspected: local ref **`origin/update-to-tapir-2.0.0` at `e7be637`**.
That was the inspected snapshot, not a promise that it is still the latest remote
tip on the next computer.

For the read command, the update is small: an optional Boolean parameter and
client forwarding. Response model shapes are unchanged. The `PropertyValue`
description was updated to acknowledge command-dependent formatting.

Important implementation details:

- Wire field: **`useSIUnits`**.
- Python generated-client keyword: **`use_si_units`**, keyword-only.
- The backport's generated client/model defaults are **`None`**, so omission
  stays omission on the wire. Explicit `False` is still forwarded.
- This deliberately differs from the update branch's explicit `False` defaults.
  Preserve omission behavior when resolving the later merge.
- `PropertyUtilities.get_property_values_per_element_result()` and its raw helper
  accept keyword-only **`use_si_units=False`**.
- Ordinary utility callers retain display-string behavior and omit the new flag.
- Explicit SI reads reject Tapir versions below **2.0.0**; there is no localized
  string fallback.
- `PropertyValuesSource.load()` explicitly passes **`use_si_units=True`**.
- Availability remains requested, and existing row/cell error handling is retained.
- Quantity operands use SI units, **except angles use degrees**.
- Numeric evaluation still applies `float()` and exact operators. It performs
  no additional unit conversion, comma replacement, rounding or tolerance.

Main implementation and tracking locations:

- [`properties.py`](../../src/multiconn_archicad/utilities/namespaces/properties.py)
- [`sources.py`](../../src/multiconn_archicad/utilities/queries/sources.py)
- [`models.py`](../../src/multiconn_archicad/utilities/queries/models.py)
- [`generated Tapir property client`](../../src/multiconn_archicad/clients/unified_api/tapir/property.py)
- [`Pydantic command models`](../../src/multiconn_archicad/models/tapir/commands.py)
- [`TypedDict command models`](../../src/multiconn_archicad/dicts/tapir/commands.py)
- [`schema backport helper`](../../code_generation/shared/schema_patching.py)
- [`schema patch tracking`](../../code_generation/documentation/schema-patch-tracking.md)
- [`SI integration tests`](../../tests/utilities/queries/test_si_property_reads.py)

`backport_property_si_units()` is called from `apply_temporary_patches()`. It keeps
the new field in the patched schema when regenerating the pinned 1.8 client and
intentionally raises if the upstream field already exists.

**When adopting the full Tapir 2.0.0 schema:** remove this temporary helper and
its call, because 2.0.0 already defines the field. Resolve client/model defaults
deliberately to preserve omission for older callers. Do not copy entire generated
files from the update branch: those files also contain thousands of unrelated changes.

Matching generated test/schema changes were backported narrowly. A structural
check confirmed that the patched master schema differed only by the intended
read flag and `PropertyValue` description.

Validation after the backport:

- **689 utility tests passed**.
- **852 utility + orchestration unit tests passed**.
- **41 code-generation/release tests passed**.
- **3 focused generated command/model tests passed** with deep schema testing.
- Total across those non-overlapping selected groups: **896 passed**.
- Strict generation audit, Ruff and whitespace checks passed.
- The whole client-generation pipeline was not rerun as a release update.

## 3. Design discussion — recommendations, not implemented features

The user has many small applications using property get/set helpers and
understands that adopting SI reads must be intentional.

Discussed principles:

- Preserve full precision at the I/O boundary. Format only for display.
- Keep the numeric value separate from the UI label; do not parse a rounded
  label to reconstruct a value to write.
- A finite Python float -> `str()` -> Python float round trip preserves that
  Python float, but the Archicad parser and radian/degree conversions introduce
  additional boundaries and must be assessed separately.
- Display strings can permanently quantize a value when written back. Repeated
  conversions can also drift or stabilize; drift is not necessarily unbounded.
- `Decimal` does not recover precision already lost in a binary float or upstream
  conversion. Counts should retain integer semantics.
- Tolerance is comparison policy, not read/write rounding or display precision.
- Avoid silently skipping writes based only on approximate numeric equality:
  explicit assignment can also affect defaults/expression state.

An optional general immutable quantity class was discussed for shared apps:
canonical value/measure, conversion, and explicit formatting settings rather
than a single fixed `.display` property. Separate subclasses per measure or a
full units library were not judged necessary for simple get/edit/set applications.
**No such class was implemented, and the user explicitly concluded the comparison
system does not need it.**

## 4. Live experiment environment and evidence

The then-open instance was **Archicad 29 / Tapir 2.0.0**, port **19723**, project
**Untitled**. The user said the file was disposable and allowed building objects.

The MCP's old read-command schema did **not** expose `useSIUnits`, so experiments
used the updated local client directly:

```python
api = UnifiedApi(CoreCommands(port=Port(19723), host="http://127.0.0.1"))
```

On another computer, rediscover the actual instance/project/port; do not assume
that the same port identifies the same project. The scripts modify their target
project and must be used against an appropriate disposable test project.

All experiment-owned columns, custom properties, groups and classification
systems were cleaned up. The final check found the original **four elements**
remaining and no experiment classification systems or properties.

### Important: saved returns are available

Each original live round trip called Archicad. Returned values and per-cell write
outcomes were recorded. Later tolerance comparisons were performed **offline
against identical saved returns**, not by repeating live calls for each epsilon.
Re-use those records for quick evaluation of additional numerical policies.

Portable experiment files, all currently local/untracked:

- [Full experiment report](experiments/property_float_precision_2026-11-13.md)
- [Editable-property observations, gzip JSON](experiments/property_float_precision_2026-11-13.json.gz)
- [Initial geometry stress observations](experiments/property_geometry_precision_2026-11-13.json)
- [Bounded +/-10 km geometry observations](experiments/property_geometry_10km_precision_2026-11-13.json)
- [Property round-trip script](../../scripts/experiments/property_float_precision.py)
- [Geometry script](../../scripts/experiments/property_geometry_precision.py)

The report contains the evidence in more detail. This handoff includes the key
numbers so it remains useful even if copied without the raw files. Copy/sync the
linked files too if offline reanalysis or reproduction is needed.

### Editable-property experiment

Created 27 columns and five scalar custom properties: Number, Length, Area,
Volume and Angle. Inputs included zeros, negatives, small values from `1e-15`,
decimal fractions, one third, pi, normal angles and stress values up to `1e12`.
All these fixture columns were near the origin (roughly X=30..82 m, Y=30 m).

For each route, reset inputs and perform 50 set/get rounds:

1. Canonical strings written back directly.
2. Parse with `float()` and write with `str()`.
3. Parse with `float()` and write expanded decimal text using
   `format(Decimal(repr(value)), "f")`; this expands exponents without rounding
   to a fixed number of decimal places.
4. Legacy display strings written back.

Recorded **27,540 observations**, including initial reads. Failed writes were
explicitly recorded; reading the unchanged old value after failure was not counted
as a successful precision round trip. Excluding display quantization and failed
writes leaves **20,455 successful canonical-path observations**. These are repeated
samples of the same inputs, not 20,455 independent scenarios.

All successful direct canonical-property comparisons pass equal relative/absolute
tolerances of `1e-9`, `1e-10`, `1e-11` and `1e-12`.

Observed precision for successful canonical paths:

| Type | Largest relative error |
| --- | ---: |
| Number | 0 |
| Length | `2.068e-16` |
| Area | 0 |
| Volume | 0 |
| Angle | `8.493e-15` |

Among angle inputs up to 720 degrees in magnitude, repeated writes produced a
largest absolute discrepancy around `1.478e-12` degrees at `359.999999999` degrees.

Display write-back introduced much larger changes on the first round trip:

| Input | Returned after display write-back |
| --- | --- |
| Unitless `3.141592653589793` | `3.142` |
| Length/Area/Volume `0.3333333333333333` | `0.33` |
| Angle `0.3333333333333333` degrees | `0` degrees |

Do not make tolerance large enough to hide display quantization.

### Scientific notation — observed, not required scope

The float-to-`str()` route caused four rejected angle writes per cycle:
`1e-15`, `1e-12`, `1e-09`, `1e-06`. Over 50 cycles that is 200 failed writes.
Tapir returned code `-2130313112`, "Failed to set property value for element".
The same values written as expanded decimal strings or original canonical
strings succeeded. Those scientific-notation inputs also succeeded for Number,
Length, Area and Volume in this experiment.

There is no explicit broad scientific-notation promise in the helpers. Existing
`create_element_property_values()` documentation says values are converted with
`str()` without numeric formatting or unit conversion. The user said scientific
notation was not important to cover. **Do not treat this as a required SI-release
fix or expand the task into general setter/parser changes without new scope.**

### Initial geometry stress tests — historical, out-of-domain samples excluded

Created 16 geometry fixtures with 65 reference comparisons. Their distribution:

- 10 fixtures / 35 comparisons: close to the origin, within approximately 450 m.
- 3 fixtures / 15 comparisons: X/Y coordinates around 1,000 m (about 1.5 km radial).
- 3 fixtures / 15 comparisons: X/Y around 1,000,000 m (outside the latest domain).

The three million-metre cases caused the failures that originally led to the
looser recommendation. Do not use them to dictate the bounded-domain default.

| Equal relative and absolute tolerances | Initial stress geometry mismatches |
| --- | ---: |
| `1e-9` | 0 |
| `1e-10` | 1 |
| `1e-11` | 2 |
| `1e-12` | 4 |

Representative stress values:

- Expected `0.056088 m²`, returned `0.05608799991894003 m²`.
- Expected `200000 m³`, returned `200000.00000126156 m³`.

### Latest geometry tests — +/-10 km independently on X/Y/Z

Created and removed **51 additional columns**, yielding **219 reference
comparisons**. Tested positive and negative X/Y near 9.9 km, Z=-9 km, Z=5 km,
Z=8 km, and intermediate/origin positions. Vertical dimensions ranged from
`0.001 x 0.002 x 0.003 m` to `10 x 20 x 1000 m`. Slants covered 1, 20, 30, 45,
60 and 89 degrees. Sizes/offsets were chosen to keep geometry inside the box.

| Equal relative and absolute tolerances | Bounded geometry mismatches |
| --- | ---: |
| `1e-9` | 0 |
| `1e-10` | 0 |
| `1e-11` | 0 |
| `1e-12` | 6 |
| `1e-13` | 21 |

All six `1e-12` failures involved a nominal `0.175275 m³` column volume. The
largest discrepancy was `1.519312453623911e-12 m³`, about `8.668e-12` relative.
A 3 mm height at large Z differed by `6.1118e-13 m`; the absolute term handled it.
At magnitude 10,000, binary64 spacing is `math.ulp(10000.0)`, approximately
`1.819e-12 m`. Coordinate spacing alone does not bound errors in calculated
areas/volumes, which can amplify coordinate roundoff.

Native slant-property semantics were kept separate from numerical error:
creation slant zero disables slanting and the native property reports 90 degrees;
a requested 0.1-degree slant returned 1 degree on this build. Those cases were
excluded from tolerance calibration, not hidden with a large epsilon.

## 5. Proposed comparison policy: what is and is not settled

The assistant's latest recommendation is **`rel_tol=1e-10, abs_tol=1e-10`** for
floating-point architectural quantities within the user's +/-10 km coordinate
box. `1e-11` also passed; `1e-10` adds an order of absolute headroom for geometry
not represented by the simple fixtures. This is empirical evidence from one
Archicad/Tapir build, not a universal mathematical error bound.

The closeness equation is:

```python
abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
```

With absolute tolerance `1e-10`, the near-zero bands correspond to:

- Length: 0.1 nanometres.
- Area: 0.0001 square millimetres.
- Volume: 0.1 cubic millimetres.
- Angle: `1e-10` degrees.
- Unitless real: `1e-10`.

A value of `5e-11 m³` consequently compares close to zero. Very small unitless
values may also need an override. The relative term grows with magnitude.
This should not become a silent global rounding rule or a construction tolerance.

An earlier possible operator mapping was discussed:

| Operator | Possible tolerance-aware rule |
| --- | --- |
| `is` | `close` |
| `is not` | `not close` |
| `>` | `a > b and not close` |
| `>=` | `a > b or close` |
| `<` | `a < b and not close` |
| `<=` | `a < b or close` |

**This mapping is not finalized or implemented.** Later discussion explicitly
clarified that a tolerance band is a query-policy choice, not a universal
replacement for every strict comparison in every application. A continuation
should establish the intended operator contract before changing it.

Other choices still open:

- Fixed engine constants versus configurable, persisted tolerances.
- How to preserve exact semantics for Integer properties, since `NumberTest`
  currently covers both scalar Integer and Real metadata and stores a float operand.
- Appropriate query-schema/documentation implications if comparison meaning changes.
- Whether/where to offer caller overrides.

Do not introduce general unit classes, arbitrary scientific-notation support,
display formatting machinery, or unrelated engine features as prerequisites.

## 6. Continuing the work

Start by checking the actual checkout/branch and working tree. Read:

- [Query reference](../utilities/element_query_reference.md)
- [Development plan](element_queries_plan.md)
- [Live experiment report](experiments/property_float_precision_2026-11-13.md)
- [Current schema patch queue](../../code_generation/documentation/schema-patch-tracking.md)
- `NumberTest.evaluate()` in
  [`queries/models.py`](../../src/multiconn_archicad/utilities/queries/models.py)
- [`property comparison tests`](../../tests/utilities/queries/test_property_comparisons.py)

No additional live experiments are needed merely to compare epsilon candidates.
For example, offline analysis can load the saved records as follows:

```python
import gzip
import json
import math
from pathlib import Path

root = Path("documentation/development/experiments")
with gzip.open(root / "property_float_precision_2026-11-13.json.gz", "rt") as stream:
    properties = json.load(stream)
geometry = json.loads(
    (root / "property_geometry_10km_precision_2026-11-13.json").read_text()
)

observations = [
    item for item in properties["observations"]
    if item["route"] != "display-string"
    and item["write_succeeded"]
    and "actual" in item
]
observations += [
    item for item in geometry["observations"] if "abs_error" in item
]

for tolerance in (1e-9, 1e-10, 1e-11, 1e-12):
    rejected = sum(
        not math.isclose(
            item["actual"], item["expected"],
            rel_tol=tolerance, abs_tol=tolerance,
        )
        for item in observations
    )
    print(tolerance, rejected)
# Expected: 0, 0, 0, 6 respectively.
```

Relevant offline checks (use the project's Python environment):

```console
python -m pytest tests/utilities tests/orchestration/unit -q -p no:cacheprovider
python -m pytest tests/generated/test_generated_tapir_methods.py tests/generated/test_generated_tapir_models.py -k "get_property_values_of_elements or GetPropertyValuesOfElements" --schema-tests=deep -q -p no:cacheprovider
python -m code_generation.tapir.generation_audit --strict
```

To reproduce live experiments only if necessary, against a disposable project:

```console
python scripts/experiments/property_float_precision.py --port YOUR_PORT --rounds 50 --output property_float_precision.json.gz
python scripts/experiments/property_geometry_precision.py --port YOUR_PORT --suite 10km-box --output property_geometry_10km_precision.json
```

The `origin-stress` geometry suite exists to reproduce the historical data, but
it places objects outside the latest coordinate limit. Do not use it for the
current bounded-domain policy or run it by default.

## Reference sources used in the discussion

- [Python floating-point tutorial](https://docs.python.org/3.13/tutorial/floatingpoint.html)
- [Python math/isclose/ulp](https://docs.python.org/3.13/library/math.html)
- [PEP 485: approximate equality](https://peps.python.org/pep-0485/)
- [Decimal behavior](https://docs.python.org/3.13/library/decimal.html)
- [Tapir 2.0.0 property implementation](https://raw.githubusercontent.com/ENZYME-APD/tapir-archicad-automation/2.0.0/archicad-addon/Sources/PropertyCommands.cpp)

Tapir's SI formatter uses `max_digits10` and expands exponents. Its property setter
uses metres, square metres, cubic metres and decimal degrees for suffix-free
quantities. That supports compatible units, but is not a bit-for-bit round-trip
guarantee for every parser/conversion path. No numeric-unit conversion migration
has been performed on the user's other apps by this chat.
