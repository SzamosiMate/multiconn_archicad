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
- **`update tapir to <version>`:** change to the requested Tapir version and perform the complete update loop: preflight, fetch, regenerate, audit, repair, repeat until clean, scan the entire diff for new problem classes, improve safeguards where appropriate, regenerate the unified API, test, report, and prepare a pull-request title and body.

Examples are `$multiconn-codegen audit`, `$multiconn-codegen regenerate tapir`, `$multiconn-codegen regenerate unified`, and `$multiconn-codegen update tapir to 1.5.9`.

## Prepare

- For an update, determine the target Tapir version from the request. Ask for it only when it cannot be inferred. For regeneration, retain the pinned version.
- Before changing behavior, inspect the relevant parts of `code_generation/tapir/run_tapir_pipeline.py`, `code_generation/shared/schema_patching.py`, `code_generation/tapir/model_generators/03_model_cleaner.py`, `code_generation/tapir/model_generators/06_typed_dict_cleaner.py`, `code_generation/tapir/generation_audit.py`, and `code_generation/unified/api_generator/run_pipeline.py`.
- Record the pre-generation Tapir version and the public definitions in `src/multiconn_archicad/models/tapir/types.py`. Use the checked-in revision as the comparison baseline, not line positions in the working file.
- Distinguish the checked-in diff baseline, initial working outputs, and the previously used client API. Compare patched public models when assessing migrations; a raw upstream-schema difference alone does not establish a new client break. Record discrepancies explicitly, including user-provided corrections to the prior API.
- Preserve unrelated working-tree changes. Do not commit, push, or open a pull request unless requested.
- Read the [pipeline brief](../../../code_generation/documentation/archicad_api_codegen_brief.md) when architecture or output routing needs context. For an update, consult the previous release report in `code_generation/documentation/reports/` and `code_generation/documentation/schema-patch-tracking.md`. Retirement requires the correction in the target release's fetched documentation schema, not merely a merged source PR or a release tag. Keep patches whose source fixes are merged but absent from the released input.

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

Preserve existing category assignments first. The working tree, including user edits, is authoritative. Do not move an existing patch between categories during audit, regeneration, release updates, repairs, or documentation reconciliation unless the user explicitly asks to reclassify those existing patches. This applies even when the patch would receive a different category under the rules for new work, has been materially modified, or an older report describes another category. Flag discrepancies or recommend a reclassification separately; do not implement it without that scope. A general request to update Tapir or apply new-patch rules does not authorize reclassifying existing patches.

For newly introduced schema patches, use exactly one category:

- **Permanent:** extend the established creation/modification item-naming pattern. Put new entries directly in `creation_data_types` or `element_modification_datatypes` in `apply_permanent_patches`, including analogous connection payloads already covered by the creation list. Do not create a separate mixed creation/modification/response loop. This is the exception to the Temporary default for new names; it does not expand the scope of Permanent or change existing assignments.
- **Temporary:** the default for new non-breaking schema refinements. Use `apply_temporary_patches` for every other extraction introducing a new public name, including conditional variants, contextual naming, and generator collision/singularization fixes. Shared-schema and enum extractions and reference replacements also belong here, with their producers before their consumers. Record the released definition/reference changes that allow retirement, preserving existing public fields, requiredness, constraints and union behavior. A valid anonymous schema is not inherently defective, but a local naming workaround need not remain Permanent merely because its immediate trigger is a generator limitation.
- **Breaking permanent:** confirmed intentional client differences in requiredness, constraints, accepted values, payload structure, or existing public definitions. Use `apply_breaking_permanent_patches` only for an established client design choice; explain its reason and compatibility consequences. A difference from upstream alone is insufficient. Do not use this category to override the preservation of existing assignments or to justify a new naming-only patch.
- **Breaking — source review / potential error:** shape-changing patches whose justification remains uncertain and may involve a schema or local patch error. Use `apply_breaking_source_review_patches`. This flags unresolved follow-up; it does not assert an upstream defect or endorse a breaking upstream proposal.

General cleaner, formatter, audit and patch-helper repairs are generator implementation changes, not schema-patch category decisions. Keep reusable fixes in their owning layer rather than creating Permanent schema extractions to work around them. Compatibility aliases are a separate public-API preservation mechanism: retain them when retiring a Temporary patch if upstream adopts a different name.

Run the stages in this order: permanent → breaking permanent → breaking source review → temporary. Document dependencies and verify that the completed schema resolves references; do not move existing patches between categories merely to arrange dependencies.

Judge new patches against the unpatched upstream schema, separately from changes already supplied by the release. Renaming/removing existing public definitions or changing accepted payloads requires a breaking classification; naming a newly introduced shape without changing acceptance is normally Temporary, subject to the established creation/modification-list exception. If a necessary repair would require an unauthorized reclassification of an existing patch, finish independent work and report that decision instead of silently moving it.

Removing a redundant patch after verified adoption in released documentation is normal retirement, not category migration. If upstream uses a different name, verify the contract and consumers, adopt the released definition, and retain required Python compatibility names through `code_generation/shared/model_aliases.py`. Do not silently skip, overwrite, or rename stale targets.

Investigation of Tapir implementation source is outside this skill's scope. For a breaking source-review patch, record the exact schema path, affected consumers, observed transformation, and unresolved question for a separate follow-up. Do not fetch or inspect Tapir implementation source as part of this workflow. Preserve existing behavior while classification remains pending unless a local repair is independently justified by in-scope schema/generator evidence. Pending follow-up does not by itself block an otherwise completed version update.

Use existing helpers where possible. Patch helpers must validate their targets and fail loudly when the upstream schema changes; do not add conditional skips for stale patches.

When released input contains a tracked correction, inspect the unpatched definition and affected consumers before removing redundant operations. Trace renamed/moved paths and earlier naming dependencies; a guard failure alone does not prove equivalence. Retain necessary compatibility aliases in `code_generation/shared/model_aliases.py`, confirm both generated representations and unified behavior, and record the confirmed release in existing tracking. Do not fetch C++ implementation source for retirement checks; unresolved source questions belong to the upstream follow-up.

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

Use the smallest naming correction that resolves the demonstrated problem. Do not add role suffixes such as `Update` solely because they sound better when singularization alone fixes the name and no collision remains. When a necessary naming or reuse decision is clear from the schema and consumers, implement it and report the resolution; otherwise preserve a valid generated name. When multiple materially different choices remain plausible, preserve the best safe generated result and ask a focused human-review question.

If the run exposes a deterministic failure class not covered by the audit, or a semantic failure class not covered by the list above, record it under `New patterns noticed`. State whether it should become a deterministic audit rule or a maintained semantic-review error type. A new instance of a known error type is not a new pattern.

### Regenerate the unified API and test

- For `regenerate tapir` and `update tapir`, run unified generation once after the Tapir audit/repair loop is clean. Do not regenerate it after every intermediate Tapir repair.
- For `regenerate unified`, run the unified pipeline directly against the current generated models.
- Run `python -m code_generation.unified.api_generator.run_pipeline` with the project environment's Python.
- If the pipeline fails because an existing file under `src/multiconn_archicad/clients/unified_api` imports a Tapir model that the finalized Tapir pipeline renamed or removed, confirm the stale name from the traceback and generated Tapir definitions. Remove only that stale import as a temporary bootstrap edit, then immediately rerun the unified pipeline so generated output replaces the manual edit.
- Do not remove imports speculatively. If the traceback does not prove this known stale-import case, or the retry fails for another reason, diagnose it normally.
- When output routing changes, verify that command literals target `src/multiconn_archicad/clients/core/literal_commands.py` and unified output targets `src/multiconn_archicad/clients/unified_api`, matching the modules imported by the client. A successful pipeline alone does not establish that the consumed package was updated.
- After successful unified generation, automatically stage newly created generated Python files under `src/multiconn_archicad/clients/unified_api/`. Identify untracked or newly added paths in that directory, verify their generated-file header and pipeline ownership, and use `git add -- <exact paths>` for those files only. Do not stage unrelated files or modifications to previously tracked unified API files. Preserve existing staged changes. This applies to Tapir updates and either regeneration operation; audit-only work stays read-only.
- Run the relevant tests only after unified generation succeeds. For Tapir regeneration or update, run the full project test suite unless the user requested a narrower scope. For standalone unified regeneration, run the generated unified-method tests and any tests covering changed generator code.

### Check reproducibility proportionally

Keep the complete-pipeline reproducibility check. When changing test-schema dependency traversal or investigating ordering noise, add a focused check in separate processes with different `PYTHONHASHSEED` values. A same-process rerun can miss randomized set iteration. Compare contents and ordering at the affected collector; do not claim whole-pipeline cross-process reproducibility from a focused check. Avoid routine repeated full-suite runs or unrelated generator/lint cleanup.

## Review the result

Compare public definitions structurally so ordering-only changes do not look semantic. Review added, removed, renamed, and changed definitions, and investigate unexplained generated-file movement or other diff noise.

Start with a release-level API summary: counts and names of added, removed, and structurally changed commands and type models. Keep aggregate facts here, separate from individual change entries. Separate new/changed/removed patch counts from unchanged inventory, state whether they count declarations or expanded loop operations, and distinguish classification-only changes from generated behavior changes.

Organize patch decisions under headings describing the **reason to patch**, rather than the API domain or lifecycle category. Reasons include preserving existing public names, naming conditional variants without losing requiredness, preventing collisions between distinct contracts, replacing generic or path-derived names, sharing equivalent contracts, and retiring released refinements while retaining compatibility. Choose reasons demonstrated by the current run; do not force a fixed inventory of headings. The same domain may appear under several reasons, and different domains may share a reason when the justification is the same. A shared helper or domain alone is insufficient justification for grouping.

Label each reason group with its Permanent, Temporary, Breaking permanent, Breaking source review, or retired classification and operation count/unit; when classifications differ within one reason, label the individual entries. This is report organization only: preserve existing patch assignments and pipeline execution order. Identify the source, affected consumers, observed problem and resolution for each decision. Give its exact schema definition/property path once, either as a JSON pointer or through a patch call whose parent and path identify it unambiguously.

Place each explanation immediately beside its actual patch calls, model excerpt or diff, normally explanation followed by code. Keep the code for a reason with that reason; do not collect all explanations first and move their code into a separate section or appendix. Apply this pairing to permanent-list entries, retired patches and compatibility aliases, generator/audit repairs, and handwritten runtime adaptations as well. Use short paragraphs and focused code blocks instead of domain inventories or prose-heavy tables. The [1.7.3 report](../../../code_generation/documentation/reports/codegen/tapir-1.7.3.md#patch-decisions-by-reason) is a format example; derive facts, reasons and counts from the current run.

Explain requiredness, unions, naming decisions, tradeoffs, temporary retirement conditions, intentional breaking behavior, and unresolved source-review questions alongside their entries. Explain each issue once; do not repeat it in separate detailed notes, semantic-review tables, or patch summaries. Keep unchanged permanent patches out of new upstream recommendations.

When upstream follow-up remains, add a short `Upstream follow-up` section linking the relevant reason entries and existing tracking. Identify new or materially changed temporary candidates and unresolved source-review questions; distinguish them from submitted fixes and merged fixes awaiting release. Include original paths when earlier naming patches obscure them. This hands work to a separately requested `$multiconn-upstream-patches` run; do not invoke that workflow automatically or duplicate its investigation here.

Classify **Unified API breaking changes** separately from schema patch categories. Compare signatures and generated return/unwrapping behavior against the baseline, including referenced model changes even when annotations stay the same. Include removed/renamed methods, changed required arguments, incompatible parameter models/types, and changed return shapes. A new optional response field that changes single-field unwrapping is a Unified API break even when the upstream addition is non-breaking. Appended optional arguments and new methods are normally additive.

Distinguish wire-schema acceptance from Python compatibility: widening an enum does not narrow JSON acceptance, but replacing its Python enum class can change equality and validation of enum instances. Do not present an enum-to-enum change as a new string-to-enum migration.

Use a dedicated `Unified API breaking changes` section with a short entry per affected method: before/after behavior and concrete caller migration. Identify the exact schema source and cause here or refer to the relevant reason entry. This section owns migration; the reason entry owns the patch decision. Count breaks separately in the API summary, and do not hide them only among upstream additions.

When handwritten generator, cleaner, formatter, or audit behavior changes, explain its trigger, input-to-output transformation, owning layer, affected models, settings considered, and deliberate limitations. Omit this section when none changed.

For the untouched new-type inventory, use `src/multiconn_archicad/models/tapir/types.py`. Include only names added relative to the checked-in baseline and untouched by patches or generator/cleaner changes made during the run. Exclude command models and repeated TypedDict names. Check representation consistency and report mismatches. List names only, without rationale.

## Report for human review

For release updates, maintain one final reviewed report at `code_generation/documentation/reports/tapir-<version>.md`, alongside the changes it explains. Revise that report during the same update rather than saving each intermediate attempt. Keep ongoing patch dispositions in `code_generation/documentation/schema-patch-tracking.md`; link instead of repeating its inventory. Preserve historical reports as records of their stated baselines and verification. Keep intermediate logs, snapshots and test output in untracked scratch storage. Audit-only work remains read-only and can report in the response. Automatically stage the final reviewed release-update report with `git add -- code_generation/documentation/reports/tapir-<version>.md`, and restage it after final revisions. Together with newly generated unified API files described above, stage only the final report; leave other files and existing staged changes alone. Do not commit unless requested.

Use the compact structure below. Retain the API summary, verification, and human-review outcome; omit other empty sections and reason headings. Avoid wide tables, repeated inventories, and routine success narration. Use actual patch calls, model excerpts, signature diffs, or caller examples when they clarify a change. Label abbreviated excerpts; do not invent executed code or validation results. Distinguish formatter success from lint findings and limited checks from broader claims.

````markdown
## Tapir generation report

**Result:** Ready for human review | Blocked · **Tapir:** <old version> → <new version>

### API change summary

- Commands: <counts and names added, removed, and structurally changed>
- Type models: <counts and names added, removed, and structurally changed>
- Unified API breaks: <count and affected methods>
- Patches: <new/changed/removed counts by category, count units, unchanged inventory>

### Patch decisions by reason

#### <Specific reason to patch>

**<Lifecycle category> - <operation count and unit>.** <Source, affected consumers,
observed problem and resolution. Include relevant requiredness, union/reuse
decisions and compatibility consequences here.>

```python
# Actual patch calls or model excerpt for this reason, directly beside its explanation.
```

<Retirement condition or decision needed, when relevant.>

<Repeat for other reasons, combining domains only when the reason is the same.
Retain Permanent/Temporary/breaking/retired labels and counts within these groups;
do not use domains or lifecycle categories as the organizing headings. Place
retired patch aliases beside their retirement explanation as well.>

#### Upstream changes — no local patch

- **<related API addition/change>.** <Concise behavior and exact source.>

### Unified API breaking changes

- **<method>.** <Before → after; refer to the reason entry for its cause.>

```python
# Concrete caller migration.
```

### Untouched new type models

- <ModelName>

### Generator and audit changes

- **<changed behavior>.** <Trigger, transformation, owning layer, affected models,
  settings considered, and limitations; only when changed.>

```diff
# Actual focused diff beside the explanation; also pair runtime adaptations with code.
```

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

## Prepare a pull-request message

For a completed Tapir version update, prepare a title and copyable Markdown body
alongside the final report. For other operations, prepare them when requested.
Keep the draft in untracked scratch storage and return its path and title. Preparing
the message does not authorize staging beyond the final report and new generated
unified API files described above,
committing, pushing, or opening a PR.

Use `Update to Tapir <version>` unless the user supplies a title or the final scope
calls for a different one. Base the body on the full proposed diff against the
intended PR base, including earlier commits on the branch and relevant uncommitted
or new files. Reconcile report claims with the current working tree; do not copy
stale counts, category assignments, or abandoned approaches. Rewrite the title and
body when scope changes.

Follow the descriptive style in the release skill's
[release-note guidance](../prepare-github-release/references/release-notes.md).
Recent update PRs [#83](https://github.com/SzamosiMate/multiconn_archicad/pull/83),
[#78](https://github.com/SzamosiMate/multiconn_archicad/pull/78), and
[#76](https://github.com/SzamosiMate/multiconn_archicad/pull/76) show the established
summary, command-table, changed-behavior, and caller-migration structure. When
available, inspect the latest comparable PRs in the actual origin repository;
resolve repository redirects before concluding that history is unavailable.
References guide style; the current diff establishes the facts.

- Start with the previous/target Tapir versions and the main capabilities added.
- List new commands in `Command | Description` tables, grouped by domain when
  useful. Use exact names, one-sentence descriptions, and material Archicad version
  restrictions. Distinguish similarly named APIs such as `Graphic` and `Graphical`.
- Describe meaningful existing-command changes separately. Put incompatible
  parameter, model, enum, and return-shape changes in `Caller migrations`, with
  before/after behavior and short caller examples where helpful. Include restored
  validation constraints affecting existing callers.
- Summarize meaningful generator, audit, and patch-retirement changes for review;
  link the repository-relative generation report for detailed decisions and model
  inventories. Include separately retained generator work when it is in the PR.
- Keep validation results and their limits in the generation report. Do not add
  a validation, testing, or verification section to the PR message.
- Omit empty sections, repeated feature lists, redundant body titles, local
  absolute paths, and speculative compatibility claims. Do not run release helpers
  or add release-only autogenerated attribution/changelog sections to a PR body.

Return the finished title and body, or a directly usable Markdown file link. When
copyable Markdown in chat is requested, use one fenced `markdown` block for the
body. Publish only when separately authorized; pass a prepared file to `gh` with
`--body-file` rather than interpolating multiline Markdown into a shell command.
