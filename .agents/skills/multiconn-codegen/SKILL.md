---
name: multiconn-codegen
description: "Explicit-use only. Audit, regenerate, update, and review the generated Tapir schemas and Python models in multiconn_archicad. Use only when the user directly invokes or names multiconn-codegen; do not select it implicitly for adjacent generator work or ordinary hand-written model edits."
---

# MultiConn Tapir code generation

Regenerate the Tapir API from its upstream schema, resolve generation problems at their source, and leave a concise report for human review. Keep the workflow and audit lightweight: a small number of reliable checks is more valuable than broad heuristic linting.

## Invocation policy

Treat this skill as explicit-only in every harness. Follow it only when the user directly invokes or names `multiconn-codegen`; do not activate it merely because a request resembles one of its operations. Harness-specific metadata may enforce this mechanically, but this instruction remains authoritative when that metadata is unsupported.

## Choose the operation

Interpret the text following the skill invocation as one of three operations:

- **`audit`:** inspect the currently generated Tapir schema and models, run the generation audit, scan the existing generated diff when present, and report findings. Keep this operation read-only unless the user also asks for repairs.
- **`regenerate tapir`:** regenerate the currently pinned Tapir version, run the audit and reproducibility check, repair generation failures at their source, and report the result. Do not change the Tapir version.
- **`update tapir to <version>`:** change to the requested Tapir version and perform the complete update loop: preflight, fetch, regenerate, audit, repair, repeat until clean, scan the entire diff for new problem classes, improve safeguards where appropriate, test, and report.

Examples are `$multiconn-codegen audit`, `$multiconn-codegen regenerate tapir`, and `$multiconn-codegen update tapir to 1.5.9`.

## Prepare

- For an update, determine the target Tapir version from the request. Ask for it only when it cannot be inferred. For regeneration, retain the pinned version.
- Before changing behavior, inspect the relevant parts of `code_generation/tapir/run_tapir_pipeline.py`, `code_generation/shared/schema_patching.py`, `code_generation/shared/model_cleaner.py`, `code_generation/shared/typed_dict_cleaner.py`, and `code_generation/tapir/generation_audit.py`.
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
   audit:      python -m code_generation.tapir.generation_audit --strict
   regenerate: python -m code_generation.tapir.run_tapir_pipeline --check-reproducibility
   update:     python -m code_generation.tapir.run_tapir_pipeline --tapir-version <version> --check-reproducibility
   ```

2. For audit-only work, run the audit against the current outputs without regenerating them. For regeneration or update, let the complete pipeline and audit report all findings. Do not stop after resolving only the first audit finding.
3. Diagnose every finding from the unpatched schema, patched schema, generator code, and generated diff. Never edit generated Python files directly.
4. Make the smallest source change that fixes the whole class of problem, then rerun the complete pipeline. Continue until the strict audit, reproducibility check, formatter, and relevant tests pass.
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

An observed one-off or subjective naming concern belongs in the human report. Do not encode it as a narrow special case. Do not edit this skill automatically; suggest a skill change only when the workflow itself proved inadequate.

## Review the result

Compare public definitions structurally so ordering-only changes do not look semantic. Review added, removed, renamed, and changed definitions, and investigate unexplained generated-file movement or other diff noise.

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

### Generated API changes requiring review

| Change | Schema source | Resolution | Patch category |
|---|---|---|---|
| `<added, removed, or renamed model>` | `<definition or property path>` | `<what changed>` | `<Permanent, Upstream-breaking, Temporary, or N/A>` |

### Untouched new type models

| Model |
|---|
| `<ModelName>` |

### Patch changes

- `<counts and short summary by category, or None>`

### Audit changes

- `<new deterministic checks, or None>`

### New patterns noticed

- `<subjective concern or candidate audit rule and recommended action, or None>`

### Verification

- Generation audit: `<result>`
- Reproducibility: `<result>`
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
