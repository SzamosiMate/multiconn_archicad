# Archicad API code-generation brief

This document describes the implemented pipelines and the boundaries between upstream schemas, local patches, generated models and the unified client. Pipeline entry points and path modules are authoritative when implementation changes. Release-specific decisions belong in [reports](reports/); ongoing patch retirement belongs in [schema-patch-tracking.md](schema-patch-tracking.md).

## Entry points and execution

Run commands from the repository root with the project environment active. On Windows, `.venv/Scripts/python.exe` can replace `python`; formatting stages also need the environment's `ruff` executable on `PATH`. Development dependencies are declared in `pyproject.toml`.

| Operation | Command |
| --- | --- |
| Audit current Tapir outputs without generating | `python -m code_generation.tapir.generation_audit --strict` |
| Regenerate pinned Tapir release | `python -m code_generation.tapir.run_tapir_pipeline --check-reproducibility` |
| Update the Tapir pin and regenerate | `python -m code_generation.tapir.run_tapir_pipeline --tapir-version <version> --check-reproducibility` |
| Regenerate Official models from downloaded inputs | `python -m code_generation.official.run_official_pipeline` |
| Refresh Official downloaded inputs explicitly | `python -m code_generation.official.model_generators.01_crawl_site` |
| Regenerate unified methods and method tests | `python -m code_generation.unified.api_generator.run_pipeline` |
| Execute the full project test suite | `python -m pytest tests -q` |

The model pipelines generate tests; they do not execute pytest. Neither model pipeline automatically runs unified generation. Finish a Tapir update with unified generation and test execution after the model audit/repair loop is clean. Tapir fetching needs network access; mock HTTP integration tests need localhost socket access.

The repository's `multiconn-codegen` skill governs explicitly requested Tapir/unified generation and review. The separate `multiconn-upstream-patches` skill investigates implementation-source changes when that workflow is requested; a model update does not automatically start upstream work.

## Tapir model pipeline

Stage order is declared in [`tapir/run_tapir_pipeline.py`](../tapir/run_tapir_pipeline.py). [`tapir/paths.py`](../tapir/paths.py) defines release URLs, intermediate files and consumed outputs.

1. **Schema generation (`01_schema_generator`).** Fetch `common_schema_definitions.js` and `command_definitions.js` from the pinned Tapir tag; parse `gSchemaDefinitions` and `gCommands`; normalize upstream `double` to `number`; rewrite local references to `#/$defs/`. Combine common definitions with command parameters/results. Save `tapir_unpatched_schema.json` before local patches, apply the four patch stages, then save `tapir_master_schema.json`.
2. **Code generation (`02_generate_dicts_and_models`).** Run `datamodel-code-generator` twice: Pydantic V2 models using `APIModel`, and TypedDicts. Pydantic generation uses ordinary `field: Type = Field(...)` declarations (`use_annotated=False`), retains explicit descriptions and constraints in `Field`, collapses root models and generally emits multi-value enums as enum classes; TypedDict generation retains root aliases and uses literals for enums. Raw files go to `tapir/temp_models/`.
3. **Pydantic cleanup (`03_model_cleaner`).** Convert remaining root wrappers to aliases; restore named reference-only unions collapsed into consumers; strip incompatible UUID pattern constraints; remove redundant model configuration; assemble headers. UUID cleanup uses AST positions to edit only the matching `Field` keyword in assignment or `Annotated` syntax, including nullable UUIDs. String-field patterns such as classification dates remain intact.
4. **Pydantic split (`04_split_models`).** Write public `types.py` in generator dependency order; write `commands.py` in alphabetical definition-name order, importing its common dependencies. Append validated compatibility aliases from the shared registry.
5. **TypedDict cleanup (`06_typed_dict_cleaner`).** Reorder recognized forward-referencing list aliases after their item definitions, remove those aliases' string forward references, and assemble the cleaned file.
6. **TypedDict split (`07_split_typed_dicts`).** Apply the same ordering policy to the corresponding public modules and append the same compatibility aliases.
7. **Model-test generation (`08_generate_model_tests`).** Generate Hypothesis tests for command models and their schema dependencies. Check payloads with Typeguard and Pydantic, using `TypeAdapter` for aliases/unions.
8. **Formatting (`09_run_formatter`).** Normalize docstring spacing, run Ruff formatting on the four final model/dictionary files and perform the final spacing pass. Formatting success does not establish lint success.
9. **Strict generation audit.** Check schema identifiers, local reference resolution, generated Python syntax and naming artifacts such as numeric suffixes or `Datum`. This is not semantic review or test execution.

Command membership comes from actual input/output schemas, not a static inventory of every extracted model. Patched definitions whose names are not command parameter/result names become common types. The schema stage also writes name lists, command metadata and command literals at the path imported by the client.

Both code-generator calls retain `keep_model_order=False`. Alphabetizing commands happens after splitting, when their common types are explicit imports, so shared-type extraction or enum refactoring no longer changes command placement. Common models retain dependency order for aliases and forward references. This stabilizes the final Tapir command modules; intermediate combined files and common-type files can still move when dependencies change.

An explicit version argument updates `SUPPORTED_TAPIR_VERSION` in `src/multiconn_archicad/constants.py`; the runner also synchronizes the README badge. Without that argument, the version remains pinned. The unpatched schema is consolidated and normalized released documentation, not Tapir implementation source or upstream `main`.

With `--check-reproducibility`, the complete Tapir stage sequence runs a second time and compares bytes of the outputs enumerated by `TapirApiPaths.generated_outputs()`: schemas, metadata, intermediate/final models, literals and model tests. It does not include unified outputs or prove cross-process reproducibility under different hash seeds.

## Patch ownership and naming

[`shared/schema_patching.py`](../shared/schema_patching.py) applies stages in this order:

| Stage | Purpose |
| --- | --- |
| Permanent | Generator workarounds and deliberate local names preserving the upstream acceptance contract |
| Breaking permanent | Confirmed intentional client contract differences |
| Breaking source review | Shape-changing differences whose justification remains unresolved |
| Temporary | Independently justified upstream corrections or shared-schema improvements, with concrete retirement conditions |

Incorrect singularization, numeric collision suffixes and names needed only by this generator are local Permanent workarounds. Valid upstream inline schemas are not defects merely because the generator names them poorly. Correct only the necessary part of a name: `ElementWithMarkerParameters` fixes one element carrying multiple parameters without adding an unnecessary `Update` suffix. A broader upstream extraction policy is separate work that must be explicitly in scope.

Keep creation, modification and response types separate when fields, requiredness or constraints differ. Reuse definitions only when concept and contract match. Put model-specific repairs in schema patches and general generator repairs in cleaners. Document dependencies when a reference points to a definition extracted in a later stage.

Helpers reject missing or already referenced targets. Extractions reject existing destination names; enum extraction raises if its enum disappeared; union helpers validate target shapes. Redundant patches must raise rather than skip or overwrite upstream definitions. Keep patch calls on one physical line, with a statement-level formatter skip when required.

Retire a patch only after confirming its correction and consumers in the target release's fetched schemas. A merged source PR or release tag alone is insufficient. Retain necessary public-name aliases in [`shared/model_aliases.py`](../shared/model_aliases.py); both Tapir splitters reject alias collisions and missing targets.

## Official model pipeline

[`official/run_official_pipeline.py`](../official/run_official_pipeline.py) currently starts with master-schema assembly. **Its crawler stage is commented out**, so regeneration consumes previously downloaded files in `official/base_schema/`. Refresh inputs explicitly when needed; a normal run is not a fresh upstream fetch.

Enabled stages assemble `official_api_master_schema.json`, build command metadata, generate Pydantic/TypedDict files, clean and split both representations, generate Official model tests, and run the shared formatter. Paths are defined in [`official/paths.py`](../official/paths.py).

Official cleaners have their own repairs, including readable `RenameNavigatorItem` variants, wrapper names, numeric enum-member names and Pydantic UUID-pattern handling. Its TypedDict cleaner decorates `AddOnCommandParameters` and `AddOnCommandResponse` with `@extra_items(Any)` for arbitrary add-on payload properties. These are not Tapir cleaner features.

The Official runner does not currently include the Tapir strict-audit or complete-pipeline reproducibility steps. Successful Official generation does not establish those guarantees.

## Unified API pipeline

[`unified/api_generator/run_pipeline.py`](../unified/api_generator/run_pipeline.py) consumes current models and command metadata from both providers. Its five subprocess stages stop on failure:

1. **Organize commands.** Merge provider metadata, omit Developer Commands, and separate element creation/modification groups. Write `unified/temp_files/01_organized_commands.json`.
2. **Generate method code.** Inspect Pydantic models to derive required/optional arguments, annotations, payload construction, result handling, docstrings and dependencies. Write `02_commands_with_code.json`. Official `RenameNavigatorItem` has an explicit union handler; unsupported parameter-root unions raise.
3. **Assemble modules.** Write grouped provider modules and `api.py` to `src/multiconn_archicad/clients/unified_api/`.
4. **Format outputs.** Run Ruff formatting on the generated unified package.
5. **Generate method tests.** Generate Official/Tapir tests using schema-derived input/response data and mocked core command methods.

Parameters serialize in JSON mode with wire aliases and omitted `None` values. Official calls route through `post_command`; Tapir calls use `post_tapir_command`. Responses are validated through models or `TypeAdapter`, including aliases and unions.

Return shape is part of the Python API: a one-field response model is unwrapped, a multi-field model is returned as a model, an empty response model yields `None`, and alias/union results are validated directly. An optional second response field can therefore change a unified return shape even when upstream acceptance changes additively. Review behavior as well as annotations.

If stale unified imports prevent generation after a finalized Tapir rename, confirm the missing name from the traceback. Remove only that stale import as a bootstrap, then immediately regenerate to replace the temporary edit. Do not routinely edit generated methods or remove imports speculatively.

## Runtime and verification limits

Generated Pydantic classes inherit [`APIModel`](../../src/multiconn_archicad/models/base.py). Its defaults include ignored extra keys, wire-alias serialization and rejected non-finite numbers; registered mixins can change configuration. `model_dump()` omits `None` by default. TypedDicts do not validate themselves; generated tests use Typeguard.

Tapir field descriptions remain explicit runtime metadata for consumers such as MCP tool schemas. They do not depend on attribute-docstring extraction or source inspection. Read them through `Model.model_fields` or `model_json_schema()`; raw type annotations no longer carry the outer `Field` metadata. `Annotated` remains supported for cases that need metadata on nested types, rather than an entire field. Official generation retains its separate settings.

Representations intentionally differ in some mechanics: UUID objects versus wire strings, enum classes versus literals, optional fields versus `NotRequired`, and singleton-literal defaults. Compare wire names, fields, requiredness and accepted values with these settings in mind. A Python union is not a complete JSON Schema `oneOf` validator, particularly with ignored extra properties.

Hypothesis generation uses copied test schemas with targeted recursion bounds or representative branches. Some Tapir tree tests bound children to empty arrays, and `GetDetailsOfElementsResult` tests select wall details rather than the full type union. These accommodations do not change the runtime schema or prove coverage of every recursive/polymorphic payload. Inspect the relevant test generator when changing them.

After audit passes, review added/changed public models, consumers, alias preservation, requiredness, enum identity and return unwrapping. Distinguish the checked-in diff baseline, initial working changes and the actual previous client API. An upstream difference already corrected by a local patch is not a new client migration. Widening wire enum values can still replace a Python enum class and affect member equality or validation.

Run pytest after unified generation. Scope full-suite collection to `tests/` to avoid scratch snapshots. Distinguish generated/mocked checks from live Archicad validation, formatting from lint, and same-process reproducibility from cross-process checks. Documentation-only changes do not require rerunning generation.

## Output and record locations

```text
code_generation/
  documentation/
    archicad_api_codegen_brief.md
    schema-patch-tracking.md
    reports/tapir-<version>.md
  shared/                       # Patches, aliases, formatting
  tapir/{schema,temp_models}/    # Schemas/metadata and intermediate models
  official/
    base_schema/                # Downloaded Official inputs
    schema/
    temp_models/
  unified/
    api_generator/
    temp_files/                 # Organized commands and method metadata
src/multiconn_archicad/
  models/{tapir,official}/{types,commands}.py
  dicts/{tapir,official}/{types,commands}.py
  clients/core/literal_commands.py
  clients/unified_api/
    api.py
    {tapir,official}/
tests/generated/
  test_generated_{tapir,official}_{models,methods}.py
```

Keep the brief, patch tracking and final reviewed release reports in source control alongside the changes they explain. Maintain one final report per release and link to tracking rather than copying inventories. Preserve historical reports' stated baselines/results; revise the current report during the same release review. Intermediate reports, logs, snapshots and raw test output belong in untracked scratch storage. This convention does not reclassify existing tracked pipeline intermediates as disposable.
