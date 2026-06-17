# Archicad API Codegen & Model Architecture Brief

This document serves as the authoritative architectural blueprint and engineering reference for the Archicad JSON API code-generation and testing pipeline. It provides full context for both human developers and AI coding assistants working on the codebase.

---

## 1. Objective & Scope

The core objective of this system is to automate the generation of a clean, high-performance, and type-safe Python client library (`multiconn-archicad`) designed to communicate with:
1. **The Tapir API** (the community-driven, extended JSON interface).
2. **The Official Archicad JSON API** (Graphisoft's native automation command set).

Rather than exposing developer-facing features directly to raw, inconsistent JSON data, this repository automates the compilation of a **high-level, object-oriented API** (`UnifiedApi`) built on a foundation of robust, validation-enforced Pydantic V2 models and lightweight static analysis TypedDicts.

---

## 2. The Core Problem

Raw JSON schemas are typically too fragmented or un-pythonic to be directly consumed by code generators like `datamodel-codegen` without severe friction:
* **Inconsistent Definitions:** Some commands are split into dozens of JSON files (Official API), while others are defined as inline JavaScript variables (Tapir API).
* **Generator Artifacts:** Raw generators produce un-pythonic names (e.g., naming polymorphic variants `RenameNavigatorItemParameters1`, `RenameNavigatorItemParameters2`), redundant configuration declarations, and out-of-order forward references.
* **Validation Incompatibilities:** Pydantic V2 cannot apply regex string patterns to compiled Python `UUID` objects, which throws runtime validation exceptions for valid UUID strings.
* **Recursive Test Traps:** Deeply nested or recursive schemas (e.g., `NavigatorItem` or `ClassificationItemDetails` containing nested lists of themselves) cause property-based testing libraries (Hypothesis) to fail due to infinite recursion.
* **Dynamic / Arbitrary Fields:** The `AddOnCommand` parameters require a mechanism to allow custom extra keys for user-defined addon payloads, which normal strict types forbid.

The multi-stage architecture detailed below systematically intercepts, cleans, splits, and tests these definitions to eliminate these flaws.

---

## 3. Pipeline Architecture

The system is organized into three distinct execution tracks:

```
                  ┌──────────────────────────────────────────────┐
                  │           ARCHICAD JSON SCHEMAS              │
                  └──────┬────────────────────────────────┬──────┘
                         │                                │
                         ▼                                ▼
       ┌──────────────────────────────────┐     ┌──────────────────────────────────┐
       │     TRACK 1: TAPIR PIPELINE      │     │    TRACK 2: OFFICIAL PIPELINE    │
       ├──────────────────────────────────┤     ├──────────────────────────────────┤
       │ 1. Parse JS Defs                 │     │ 1. Crawl Graphisoft Site         │
       │ 2. Generate Master Schema        │     │ 2. Consolidate Master Schema     │
       │ 3. Pydantic / TypedDict Codegen  │     │ 3. Command Details Mapping       │
       │ 4. Clean Raw Models & TypedDicts │     │ 4. Pydantic / TypedDict Codegen  │
       │ 5. Split Types & Commands        │     │ 5. Clean Raw Models & TypedDicts │
       │ 6. Property-Based Schema Tests   │     │ 6. Split Types & Commands        │
       │                                  │     │ 7. Property-Based Schema Tests   │
       └─────────────────┬────────────────┘     └─────────────────┬────────────────┘
                         │                                        │
                         └───────────────────┬────────────────────┘
                                             │
                                             ▼
                          ┌────────────────────────────────────┐
                          │    TRACK 3: HIGH-LEVEL UNIFIED API │
                          ├────────────────────────────────────┤
                          │ 1. Stage 1: Organize Commands JSON │
                          │ 2. Stage 2: Generate Method Code   │
                          │ 3. Stage 3: Assemble Group Modules │
                          │ 4. Stage 4: Ruff Formatting        │
                          │ 5. Stage 5: Unified Method Tests   │
                          └────────────────────────────────────┘
```

---

## 4. Structural Track Details

### Track 1: Tapir API Model Generation (`code_generation/tapir/`)
Operates on the JavaScript-defined schemas of the Tapir repository:
1. **`01_schema_generator.py`**: Fetches raw Tapir JS files, parses JSON blocks, fixes reference paths recursive to `$defs`, applies permanent patches, and dynamically dispatches active schemas into base and command groups using the raw commands definition list.
2. **`02_generate_dicts_and_models.py`**: Runs `datamodel-codegen` to produce raw Pydantic V2 models and raw Python `TypedDict` objects.
3. **`03_model_cleaner.py` & `06_typed_dict_cleaner.py`**: Clean generator boilerplate, strip redundant configuration blocks, convert trivial `RootModel` instances into simple `TypeAlias` types, and correct out-of-order TypeAliases.
4. **`04_split_models.py` & `07_split_typed_dicts.py`**: Separate the massive definitions into `types.py` (common schemas) and `commands.py` (parameters/results) while maintaining correct relative order and resolving cross-file imports.
5. **`08_generate_model_tests.py`**: Automatically constructs a validation test suite using `hypothesis-jsonschema` to verify that mock data conforming to the schemas parses through both the Pydantic classes and Typeguard validation.

---

### Track 2: Official API Model Generation (`code_generation/official/`)
Handles Graphisoft's official documentation and schema files:
1. **`01_crawl_site.py`**: Crawls and downloads the official `.json` schema documents and the `menutree.json` from Graphisoft's site.
2. **`02_generate_master_schema.py`**: Assembles a consolidated `master_schema.json` file, translates remote references to local ones, and outputs lists of model names.
3. **`03_generate_command_details.py`**: Correlates the crawled files with the `menutree.json` to assign group names, descriptions, and metadata to every API command.
4. **`04_generate_dicts_and_models.py`**: Runs Pydantic V2 and TypedDict code generation.
5. **`05_model_cleaner.py` & `08_typed_dict_cleaner.py`**: 
   - Resolves ambiguous polymorphic variant names (e.g., renames `RenameNavigatorItemParameters1/2/3` to readable class definitions: `RenameNavigatorItemByName`, `RenameNavigatorItemById`, `RenameNavigatorItemByNameAndId`).
   - Standardizes members of numeric Enums (e.g., converts `field_01` to `Style01`).
   - Dynamically decorates `AddOnCommand` parameters with an `@extra_items(Any)` decorator to permit unstructured developer properties.
6. **`06_split_models.py` & `09_split_typed_dicts.py`**: Split the clean models and dicts into `types.py` and `commands.py`.
7. **`07_generate_model_tests.py`**: Auto-generates a property-based test file (`test_generated_official_models.py`) targeting the Official API types.

---

### Track 3: High-Level Unified API Pipeline (`api_generator/`)
Organizes all commands into a high-level, developer-friendly interface using five stages orchestrated by **`run_pipeline.py`**:
* **Stage 1 (`01_organize_commands.py`)**: Merges both schema tracks' metadata and structures commands into logical namespaces (e.g., element creation, modifications, layouts).
* **Stage 2 (`02_generate_method_code.py`)**: Dynamically reads the structured command data, extracts parameter and return signatures by inspecting the compiled Pydantic models, strips out typing wrappers (such as `Annotated` or validation constraints), and builds compliant Python method strings complete with type hinting, docstrings with explicit standard `Raises` blocks, and error handling.
* **Stage 3 (`03_assemble_api_files.py`)**: Builds the individual namespaced module files (e.g., `elements.py`, `attributes.py`) under the package structure, imports only the necessary model dependencies, and sets up `api.py` with aliased access containers (`self.tapir` and `self.official`).
* **Stage 4 (`04_format_output.py`)**: Runs Ruff formatter on the final package structure to enforce clean coding standards.
* **Stage 5 (`05_generate_command_tests.py`)**: Auto-generates a complete test suite that mocks core communication layers, utilizes Hypothesis to feed inputs, and verifies that the high-level methods validate parameters, route commands correctly, and parse outputs cleanly.

---

## 5. Critical Patches & Invariant Rules

To keep the pipeline robust, several manual interventions are automated:

### Dynamic Command Dispatching
When splitting model names into `types.py` and `commands.py`, we do not rely on static list comparisons which are prone to drift when patches extract new types. Instead, `01_schema_generator.py` extracts definitions directly from `commands_list` to form a lookup set (`valid_command_model_names`). Keys inside `master_defs` are then checked against this set: those present become command parameters/results, and everything else is written as base types. This naturally tracks newly-extracted models like `ColumnData` without manual updates.

### UUID Pattern Stripping
Pydantic V2 applies validation logic to `UUID` fields *after* instantiating them into objects. If a schema contains a regex pattern constraint (e.g., `^[0-9a-fA-F]{8}-...`), Pydantic attempts to match the regex against the instantiated `UUID` class object rather than the raw string, raising a validation error. The cleaners surgically strip `pattern="..."` properties off of Pydantic fields annotated as `UUID` while leaving other validation constraints intact.

### Breaking Hypothesis Recursion
The recursive types `NavigatorItem`, `ClassificationItemDetails`, `ClassificationItemInTree`, and `AttributeFolderStructure` are patched during test generation to prune the recursive child array properties (like `children` or `subfolders`). This isolates individual elements, enabling property-based test suites to run fast and complete without hitting execution time limits or infinite recursion.

### @extra_items Decoration
Graphisoft's `AddOnCommandParameters` and `AddOnCommandResponse` structures are designed to wrap arbitrary JSON objects passing through third-party C++ addons. The TypedDict cleaner decorates these definitions with `@extra_items(Any)` to allow them to handle arbitrary developer properties without raising structural validation errors.

---

## 6. Directory Layout Reference

```
multiconn_archicad/
├── src/
│   └── multiconn_archicad/
│       ├── dicts/                  # Generated & cleaned TypedDicts
│       │   ├── official/
│       │   └── tapir/
│       ├── models/                 # Generated & cleaned Pydantic models
│       │   ├── official/
│       │   └── tapir/
│       └── unified_api/            # Final assembled, high-level client
│           ├── official/
│           ├── tapir/
│           └── api.py              # UnifiedApi entry point class
├── tests/
│   └── generated/                  # Automated pytest validation files
│       ├── test_generated_official_methods.py
│       ├── test_generated_official_models.py
│       ├── test_generated_tapir_methods.py
│       └── test_generated_tapir_models.py
```


---

