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
- Before changing behavior, inspect the relevant parts of `code_generation/tapir/run_tapir_pipeline.py`, `code_generation/shared/schema_patching.py`, `code_generation/shared/model_cleaner.py`, `code_generation/shared/typed_dict_cleaner.py`, `code_generation/tapir/generation_audit.py`, and `code_generation/unified/api_generator/run_pipeline.py`.
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

- **Permanent:** required by a code-generator limitation or an intentional Python client design choice. An upstream schema correction would not make the local requirement disappear.
- **Upstream-breaking:** corrects an upstream schema problem, but the proper upstream correction changes a public schema name or shape. Use `apply_upstream_breaking_patches`. If this function does not yet exist, add it and invoke it after permanent patches and before temporary patches.
- **Temporary:** corrects an upstream problem that can be fixed without a breaking public-schema change. Remove the patch after the upstream correction arrives.

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
- If the pipeline fails because an existing file under `src/multiconn_archicad/unified_api` imports a Tapir model that the finalized Tapir pipeline renamed or removed, confirm the stale name from the traceback and generated Tapir definitions. Remove only that stale import as a temporary bootstrap edit, then immediately rerun the unified pipeline so generated output replaces the manual edit.
- Do not remove imports speculatively. If the traceback does not prove this known stale-import case, or the retry fails for another reason, diagnose it normally.
- Run the relevant tests only after unified generation succeeds. For Tapir regeneration or update, run the full project test suite unless the user requested a narrower scope. For standalone unified regeneration, run the generated unified-method tests and any tests covering changed generator code.

## Review the result

Compare public definitions structurally so ordering-only changes do not look semantic. Review added, removed, renamed, and changed definitions, and investigate unexplained generated-file movement or other diff noise.

Start the report with a release-level API summary: counts and names of added, removed, and structurally changed commands and type models. Do not put these aggregate facts in the decision table.

In the decision table, use one row per independently reviewable change. Do not group unrelated schema locations merely because they share a mechanical cause such as anonymous inline generation. Each row must identify the exact schema definition or property path, affected command or public-model consumers, the upstream shape or generated symptom, the chosen resolution, and its patch category. Add a short detailed note after the table whenever requiredness, union behavior, compatibility, or competing designs cannot be understood from one row.

Whenever handwritten generator, cleaner, formatter, or audit behavior changes, explain the new concept in the report. Include what triggered it, its input-to-output transformation, why that layer owns the fix, affected models, and its deliberate limitations. Check relevant generator settings before adding a cleaner workaround and report why no suitable setting was used.

For the new-model inventory:

- Use `src/multiconn_archicad/models/tapir/types.py` as the canonical source.
- Include only type-model names added relative to the pre-generation baseline and untouched by patches or generator/cleaner changes made during this run.
- Exclude command parameter and result models from `commands.py`.
- Do not repeat the corresponding TypedDict names. Check their consistency and report a mismatch as a problem.
- List only the names; no rationale is needed. In an ideal update, every new type model is in this table.

## Report for human review

Use this structure, omitting empty detail rows but retaining every heading. State `None` where appropriate.

```markdown
## Tapir generation report

**Result:** Ready for human review | Blocked
**Tapir:** <old version> → <new version>

### API change summary

- Commands: `<counts and names added, removed, and structurally changed>`
- Type models: `<counts and names added, removed, and structurally changed>`
- Review decisions: `<count by patch category>`

### Generated API changes requiring review

| Change | Schema source | API consumers | Upstream/generated problem | Resolution | Patch category |
|---|---|---|---|---|---|
| `<one independently reviewable change>` | `<exact definition or property path>` | `<commands and public models>` | `<relevant shape, requiredness, duplication, or generated symptom>` | `<what changed and why>` | `<Permanent, Upstream-breaking, Temporary, or N/A>` |

### Detailed decision notes

#### `<change needing more explanation>`

- Before: `<relevant upstream and generated behavior>`
- After: `<resulting public models and behavior>`
- Compatibility and tradeoffs: `<what the reviewer needs to know>`
- Decision needed: `<specific confirmation, or None>`

### Semantic naming review

| Generated name | Schema context and consumers | Finding | Resolution |
|---|---|---|---|
| `<original generated name>` | `<property path and API consumers>` | `<known semantic error type>` | `<new name, shared type, separation, or focused unresolved question>` |

### Untouched new type models

| Model |
|---|
| `<ModelName>` |

### Generator and cleaner changes

#### `<function or behavior, or None>`

- Trigger: `<observed failure>`
- Transformation: `<input to output behavior>`
- Why this layer: `<why settings or schema patches were insufficient>`
- Affected models: `<names>`
- Scope and limitations: `<what it deliberately does not change>`

### Patch changes

- `<counts and short summary by category, or None>`

### Audit changes

- `<new deterministic checks, or None>`

### New patterns noticed

- `<new deterministic or semantic error type, its example, and whether to add an audit rule or semantic-review checklist entry; or None>`

### Verification

- Generation audit: `<result>`
- Reproducibility: `<result>`
- Unified API generation: `<result, including whether a stale import bootstrap was needed>`
- Ruff: `<result>`
- Tests: `<result>`
- Unexpected generated diff noise: `<result>`

### Human review

- `<specific decisions or confirmations needed, or None>`

### Suggested skill update

None.
```

When the workflow itself should change, replace `None` in the final section with a standalone, copyable prompt:

```markdown
### Suggested skill update

Reason: <what this run exposed about the workflow>

Copy and use this prompt if you agree:

> Update the `multiconn-codegen` skill so that <specific workflow change>. Preserve <important existing constraint>. Do not <likely overreach>.
```

Keep model-specific fixes in schema patching and generally applicable deterministic checks in the generation audit. Reserve skill-update suggestions for changes to how the overall generation and review workflow should operate.
