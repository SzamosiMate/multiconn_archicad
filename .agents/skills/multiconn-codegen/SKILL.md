---
name: multiconn-codegen
description: "Explicit-use only. Audit, regenerate, update, and review the generated Tapir models and unified API in multiconn_archicad. Use only when the user directly invokes or names multiconn-codegen; do not select it implicitly for adjacent generator work or ordinary hand-written model edits."
---

# MultiConn Tapir code generation

Regenerate the Tapir API from its upstream schema, resolve generation problems at their source, and leave a concise report for human review. Keep the workflow and audit lightweight: a small number of reliable checks is more valuable than broad heuristic linting.

## Invocation policy

Treat this skill as explicit-only in every harness. Follow it only when the user directly invokes or names `multiconn-codegen`; do not activate it merely because a request resembles one of its operations. Harness-specific metadata may enforce this mechanically, but this instruction remains authoritative when that metadata is unsupported.

## Choose the operation

Interpret the text following the skill invocation as one of four operations:

- **`audit`:** inspect the currently generated Tapir schema and models, run the generation audit, scan the existing generated diff when present, and report findings. Keep this operation read-only unless the user also asks for repairs.
- **`regenerate tapir`:** regenerate the currently pinned Tapir version, run the audit and reproducibility check, repair generation failures at their source, regenerate the unified API, run tests, and report the result. Do not change the Tapir version.
- **`regenerate unified`:** regenerate only the unified API from the current Official and Tapir models, handle a stale generated import when necessary, run relevant tests, and report the result. Do not rerun either model pipeline.
- **`update tapir to <version>`:** change to the requested Tapir version and perform the complete update loop: preflight, fetch, regenerate, audit, repair, repeat until clean, scan the entire diff for new problem classes, improve safeguards where appropriate, regenerate the unified API, test, and report.

Examples are `$multiconn-codegen audit`, `$multiconn-codegen regenerate tapir`, `$multiconn-codegen regenerate unified`, and `$multiconn-codegen update tapir to 1.5.9`.

## Prepare

- For an update, determine the target Tapir version from the request. Ask for it only when it cannot be inferred. For regeneration, retain the pinned version.
- Before changing behavior, inspect the relevant parts of `code_generation/tapir/run_tapir_pipeline.py`, `code_generation/shared/schema_patching.py`, `code_generation/tapir/model_generators/03_model_cleaner.py`, `code_generation/tapir/model_generators/06_typed_dict_cleaner.py`, `code_generation/tapir/generation_audit.py`, and `code_generation/unified/api_generator/run_pipeline.py`.
- Record the pre-generation Tapir version and the public definitions in `src/multiconn_archicad/models/tapir/types.py`. Use the checked-in revision as the comparison baseline, not line positions in the working file.
- Preserve unrelated working-tree changes. Do not commit, push, or open a pull request unless requested.

### Inspect large artifacts efficiently

- Treat generated schemas, generated Python files, and large diffs as search targets rather than documents to read front to back.
- Start with diff statistics, changed paths, definition-name comparisons, and targeted searches for audit findings, added or removed names, references, and suspicious suffixes.
- Read only the changed hunk or the smallest surrounding range needed to understand a definition and its dependencies. Follow references with further targeted searches.
- Never load an entire generated schema or generated model file into context. Use parsers or short one-off scripts for structural comparisons and counts.
- Inspect the full diff conceptually by enumerating and classifying all changed definitions and hunks; this does not require printing the complete diff at once.
- Small hand-written generator modules may be read in full when their overall control flow matters.

## Generate and repair

1. Run the requested operation with the project environment's Python:

   ```text
   audit:              python -m code_generation.tapir.generation_audit --strict
   regenerate tapir:   python -m code_generation.tapir.run_tapir_pipeline --check-reproducibility
   regenerate unified: python -m code_generation.unified.api_generator.run_pipeline
   update tapir:       python -m code_generation.tapir.run_tapir_pipeline --tapir-version <version> --check-reproducibility
   ```

2. For audit-only work, run the audit against the current outputs without regenerating them. For Tapir regeneration or update, let the complete Tapir pipeline and audit report all findings. Do not stop after resolving only the first audit finding.
3. Diagnose every finding from the unpatched schema, patched schema, generator code, and generated diff. Never edit generated Python files directly except for the narrowly scoped unified-generation bootstrap described below.
4. Make the smallest source change that fixes the whole class of problem, then rerun the complete Tapir pipeline. Continue until its strict audit, reproducibility check, and formatter pass; then regenerate the unified API and run tests.
5. If a failure requires a product or public-API decision that cannot be inferred safely, finish all independent findings and report the remaining decision instead of guessing.

### Classify schema patches

Put each patch in exactly one category:

- **Permanent:** established generator workarounds or intentional client choices that preserve the upstream schema contract. Use `apply_permanent_patches`. Preserve existing intent even when an equivalent upstream refactor is technically possible; do not propose upstream changes solely to accommodate generator shortcomings such as `Data` becoming `Datum`.
- **Temporary:** fixes intended for non-breaking upstream adoption. Use `apply_temporary_patches`, record the upstream change that would allow removal, and remove the patch when that correction arrives. Naming an anonymous schema or reusing an equivalent definition may belong here when upstream adoption is intended and existing public names, fields, requiredness, constraints, and union behavior can be preserved.
- **Breaking permanent:** confirmed intentional client differences in requiredness, constraints, accepted values, payload structure, or existing public schema definitions. Use `apply_breaking_permanent_patches`. State the deliberate client behavior, its reason, and compatibility consequences; a difference from upstream alone does not establish intent.
- **Breaking — source review / potential error:** shape-changing patches whose justification remains uncertain and may involve a schema or local patch error. Use `apply_breaking_source_review_patches`. This category flags unresolved follow-up; it does not assert an upstream defect or endorse a breaking upstream proposal.

Run the stages in this order: permanent → breaking permanent → breaking source review → temporary. Document dependencies when a reference points to a definition extracted in a later stage, and verify that the completed schema resolves those references.

During an update, classify patches introduced or materially changed by that update, plus older patches explicitly requested for review. Do not reopen all established permanent classifications unless asked. Judge each patch against the unpatched upstream schema, separately from release changes already supplied by upstream. Renaming/removing existing public definitions or changing accepted payloads requires a breaking classification.

Investigation of Tapir implementation source is outside this skill's scope. For a breaking source-review patch, record the exact schema path, affected consumers, observed transformation, and unresolved question for a separate follow-up. Do not fetch or inspect Tapir implementation source as part of this workflow. Preserve existing behavior while classification remains pending unless a local repair is independently justified by in-scope schema/generator evidence. Pending follow-up does not by itself block an otherwise completed version update.

Use existing helpers where possible. Patch helpers must validate their targets and fail loudly when the upstream schema changes; do not add conditional skips for stale patches.

Keep each patch call on one physical line. Use a formatter-skip marker on that statement only when required to preserve the one-line declaration. Group patches with the same reason together. Add a short comment when introducing a new reason for patching, and reuse that heading for later patches with the same reason; do not narrate every individual call.

### Extend the audit sparingly

Always inspect the generated diff for novel mistakes, even when the audit passes. Add an audit rule only when the issue is inexpensive to detect, deterministic, broadly useful, and unlikely to produce false positives. Prefer checking schema names, references, Python syntax, and unmistakable generator artifacts over judging whether a valid name is semantically ideal.

Do not encode a subjective judgment as a narrow deterministic special case. Resolve it in the semantic review when the schema context supports a clear answer; otherwise leave a specific question for human review.

### Run an agentic semantic review

After the deterministic audit passes, inspect every added or structurally changed public model in schema context. Trace its consumers, compare it with existing public types, and repair clear semantic problems at the schema-patching or generator source. This review is required even when the audit reports no errors.

Known semantic error types are:

- context-free or overly broad names that should include their domain or role;
- mechanically derived names that describe an inline path rather than the represented concept;
- duplicate types or enums that represent the same concept and should share one public definition;
- inconsistent naming among related request, response, creation, modification, and details models;
- inappropriate model sharing that hides meaningful required/optional or request/response differences;
- a named public abstraction lost because the generator inlined or collapsed its wrapper;
- a generated representation that weakens or obscures an important schema constraint such as `oneOf`, `anyOf`, or conditional required fields;
- inconsistent Pydantic and TypedDict public surfaces.

When a better name or reuse decision is clear from the schema and consumers, implement it and report the resolution. When multiple materially different choices remain plausible, preserve the best safe generated result and ask a focused human-review question.

If the run exposes a deterministic failure class not covered by the audit, or a semantic failure class not covered by the list above, record it under `New patterns noticed`. State whether it should become a deterministic audit rule or a maintained semantic-review error type. A new instance of a known error type is not a new pattern.

### Regenerate the unified API and test

- For `regenerate tapir` and `update tapir`, run unified generation once after the Tapir audit/repair loop is clean. Do not regenerate it after every intermediate Tapir repair.
- For `regenerate unified`, run the unified pipeline directly against the current generated models.
- Run `python -m code_generation.unified.api_generator.run_pipeline` with the project environment's Python.
- If the pipeline fails because an existing file under `src/multiconn_archicad/clients/unified_api` imports a Tapir model that the finalized Tapir pipeline renamed or removed, confirm the stale name from the traceback and generated Tapir definitions. Remove only that stale import as a temporary bootstrap edit, then immediately rerun the unified pipeline so generated output replaces the manual edit.
- Do not remove imports speculatively. If the traceback does not prove this known stale-import case, or the retry fails for another reason, diagnose it normally.
- When output routing changes, verify that command literals target `src/multiconn_archicad/clients/core/literal_commands.py` and unified output targets `src/multiconn_archicad/clients/unified_api`, matching the modules imported by the client. A successful pipeline alone does not establish that the consumed package was updated.
- Run the relevant tests only after unified generation succeeds. For Tapir regeneration or update, run the full project test suite unless the user requested a narrower scope. For standalone unified regeneration, run the generated unified-method tests and any tests covering changed generator code.

### Check reproducibility proportionally

Keep the complete-pipeline reproducibility check. When changing test-schema dependency traversal or investigating ordering noise, add a focused check in separate processes with different `PYTHONHASHSEED` values. A same-process rerun can miss randomized set iteration. Compare contents and ordering at the affected collector; do not claim whole-pipeline cross-process reproducibility from a focused check. Avoid routine repeated full-suite runs or unrelated generator/lint cleanup.

## Review the result

Compare public definitions structurally so ordering-only changes do not look semantic. Review added, removed, renamed, and changed definitions, and investigate unexplained generated-file movement or other diff noise.

Start with a release-level API summary: counts and names of added, removed, and structurally changed commands and type models. Keep aggregate facts here, separate from individual change entries. Separate new/changed/removed patch counts from unchanged inventory, state whether they count declarations or expanded loop operations, and distinguish classification-only changes from generated behavior changes.

Group review entries under patch-category headings. Use short lists and actual code snippets instead of prose-heavy tables. Each independently reviewable decision needs its own entry identifying the source, affected consumers, observed problem, and resolution. Give the exact schema definition/property path once, either as a JSON pointer or through a patch call whose parent and path identify it unambiguously. Do not group unrelated locations just because they share a mechanical cause; ordinary related upstream additions with no separate decision can be summarized together.

Explain requiredness, unions, naming decisions, tradeoffs, temporary retirement conditions, intentional breaking behavior, and unresolved source-review questions alongside their entries. Explain each issue once; do not repeat it in separate detailed notes, semantic-review tables, or patch summaries. Keep unchanged permanent patches out of new upstream recommendations.

Classify **Unified API breaking changes** separately from schema patch categories. Compare signatures and generated return/unwrapping behavior against the baseline, including referenced model changes even when annotations stay the same. Include removed/renamed methods, changed required arguments, incompatible parameter models/types, and changed return shapes. A new optional response field that changes single-field unwrapping is a Unified API break even when the upstream addition is non-breaking. Appended optional arguments and new methods are normally additive.

Use a dedicated `Unified API breaking changes` section with a short entry per affected method: before/after behavior and concrete caller migration. Identify the exact schema source and cause here or refer to the relevant category entry. This section owns migration; the category entry owns the patch decision. Count breaks separately in the API summary, and do not hide them only among upstream additions.

When handwritten generator, cleaner, formatter, or audit behavior changes, explain its trigger, input-to-output transformation, owning layer, affected models, settings considered, and deliberate limitations. Omit this section when none changed.

For the untouched new-type inventory, use `src/multiconn_archicad/models/tapir/types.py`. Include only names added relative to the checked-in baseline and untouched by patches or generator/cleaner changes made during the run. Exclude command models and repeated TypedDict names. Check representation consistency and report mismatches. List names only, without rationale.

## Report for human review

Use the compact structure below. Retain the API summary, verification, and human-review outcome; omit other empty sections and category headings. Avoid wide tables, repeated inventories, and routine success narration. Use actual patch calls, model excerpts, signature diffs, or caller examples when they clarify a change. Label abbreviated excerpts; do not invent executed code or validation results. Distinguish formatter success from lint findings and limited checks from broader claims.

````markdown
## Tapir generation report

**Result:** Ready for human review | Blocked · **Tapir:** <old version> → <new version>

### API change summary

- Commands: <counts and names added, removed, and structurally changed>
- Type models: <counts and names added, removed, and structurally changed>
- Unified API breaks: <count and affected methods>
- Patches: <new/changed/removed counts by category, count units, unchanged inventory>

### Changes by patch category

#### Temporary

- **<change and consumers>.** <Problem and resolution in a short paragraph.>

```python
# Actual patch call, model excerpt, or usage example.
```

<Retirement condition or decision needed, when relevant.>

<Use the same entry format for nonempty Permanent, Breaking permanent,
Breaking — source review / potential error, and Removed patches groups.>

#### Upstream changes — no local patch

- **<related API addition/change>.** <Concise behavior and exact source.>

### Unified API breaking changes

- **<method>.** <Before → after; refer to the category entry for its cause.>

```python
# Concrete caller migration.
```

### Untouched new type models

- <ModelName>

### Generator and audit changes

- **<changed behavior>.** <Trigger, transformation, owning layer, affected models,
  settings considered, and limitations; only when changed.>

### New patterns noticed

- <New deterministic/semantic error type and whether to extend the audit or
  semantic-review checklist; omit when none.>

### Verification

- Audit and reproducibility: <results and scope>
- Unified generation: <result, output routing, any stale-import bootstrap>
- Ruff: <formatting result and any lint findings>
- Tests: <result and scope>
- Representation consistency and diff review: <result and any remaining noise>

### Human review

<Specific unresolved decisions, or "No pending decisions.">
````

Only when the workflow itself should change, append a standalone, copyable prompt:

```markdown
### Suggested skill update

Reason: <what this run exposed about the workflow>

Copy and use this prompt if you agree:

> Update the `multiconn-codegen` skill so that <specific workflow change>. Preserve <important existing constraint>. Do not <likely overreach>.
```

Keep model-specific fixes in schema patching and generally applicable deterministic checks in the generation audit. Reserve skill-update suggestions for changes to the overall generation and review workflow.
