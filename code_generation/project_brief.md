### **Project Brief: Unified Archicad API Model Generation Pipeline**

#### **1. Objective**

To automate the creation of a high-quality, consistent, and type-safe Python library for interacting with **both** the community-driven **Tapir API** and the **Official Archicad JSON API**. The primary goal is to provide a superior developer experience by transforming complex, fragmented JSON schemas into a complete, high-level, pythonic client, built upon a foundation of clean Pydantic models and TypedDicts.

---

#### **2. The Core Problem**

Directly using the Archicad JSON APIs in Python is challenging for several reasons:
*   **Schema Fragmentation:** The API definitions are spread across multiple files (JavaScript variables for Tapir, dozens of individual JSON files for the Official API).
*   **Schema Complexity:** The schemas contain complex structures, including recursive definitions, conditional types (`oneOf`), and inconsistent naming, which are not directly usable.
*   **Generator Artifacts:** Standard code generation tools like `datamodel-codegen`, while powerful, produce un-pythonic code with numerous artifacts that need to be cleaned. These include keyword collisions (`copy` -> `copy_`), invalid identifiers (`3DModel`), inconsistent naming conventions, and boilerplate configurations.

This project solves these problems by creating an automated, multi-stage pipeline that ingests the raw schemas and outputs a pristine, developer-friendly Python client library.

---

#### **3. Solution Overview: A Multi-Pipeline Architecture**

The solution is a robust architecture composed of **three distinct pipelines** that build upon each other to produce a layered, high-quality library. This design allows each pipeline to handle specific challenges while ensuring the final output is consistent and cohesive.

**Key Deliverables:**

*   **A High-Level `UnifiedApi` Client:** The cornerstone of the library. It provides a fully-typed, object-oriented interface organized into a clear, two-level namespace (`api.tapir.<group>`). It features pythonic `snake_case` methods for all commands and handles data validation transparently, accepting simple inputs and returning validated Pydantic models.
*   **Strict Pydantic Models:** For runtime validation and data parsing (`models/tapir/` & `models/official/`). These `camelCase` models serve as the direct, validated representation of the API schemas. All models inherit from a custom `APIModel` base class that enforces strict validation (`extra='forbid'`).
*   **TypedDicts:** For lightweight static analysis and type hinting (`dicts/tapir/` & `dicts/official/`). These provide type safety for the low-level, dictionary-based `core` command interface.
*   **Command Metadata:** Structured JSON files detailing command names, groups, and descriptions (`_command_details.json`), which serve as the input for the `UnifiedApi` pipeline.
*   **Command Literals:** `literal_commands.py` files providing `Literal` types for all command names.
*   **Symmetric Runtime Validation Suite:** A unified, auto-generated test suite that performs **symmetric runtime validation** for both Pydantic models and TypedDicts, ensuring they remain perfectly in sync with the source schemas.

---

#### **4. Pipeline Architecture**

The project consists of three distinct pipelines:

##### **Track 1 & 2: Tapir and Official API Model Generation**

These two parallel pipelines are responsible for creating the foundational models.
1.  **Fetch/Crawl & Parse:** Each pipeline downloads its respective source schemas.
2.  **Generate Master Schema:** The raw schemas are merged into a single, self-contained `master_schema.json` for each API.
3.  **Generate Code:** `datamodel-codegen` is used to produce the initial Pydantic models and TypedDicts.
4.  **Surgical Cleaning:** A series of rule-based cleaning scripts apply targeted fixes, normalize Enum members, remove boilerplate, and ensure all models inherit from the strict `APIModel` base class. This stage also intelligently configures `ExecuteAddOnCommand` to allow `additionalProperties` for dynamic parameters.
5.  **Split Models:** Intelligent splitter scripts separate the cleaned files into `types.py` and `commands.py`, automatically generating the necessary cross-file imports.

##### **Track 3: High-Level `UnifiedApi` Generation**

This final pipeline is a **multi-stage process** that consumes the outputs of the first two tracks to build the high-level client, using intermediate JSON artifacts for transparency and debugging.

1.  **Stage 1: Organize Commands:** The script reads the `_command_details.json` files and organizes all commands into a structured JSON artifact, grouped by source (`tapir`/`official`) and functional area (`attributes`, `elements`, etc.).
2.  **Stage 2: Generate Method Code:** This core stage reads the organized JSON and, for each command, generates a complete Python method string. It simultaneously tracks all Pydantic model dependencies. The output is a new JSON artifact containing all the original data plus the generated code and dependency lists.
3.  **Stage 3: Assemble Files:** This final stage reads the enriched JSON from Stage 2 and writes the complete `unified_api` package. It creates a file for each command group and assembles the top-level `api.py`, aliasing imported classes (e.g., `TapirAttributeCommands`) to resolve name collisions.

This pipeline engineers a user-friendly API by design:
*   **Method Signature:** It uses Python's `inspect` module on the Pydantic models to create clean, `snake_case` method signatures with correctly ordered parameters. **Crucially, it strips validation metadata like `Annotated` from the signature**, presenting a simple type to the user.
*   **Docstrings:** It generates comprehensive docstrings with command descriptions, parameter details, and a standardized **`Raises` section** that clearly documents the API's exception contract (`ArchicadAPIError`, `RequestError`). Validation constraints (e.g., `min_length`) are cleanly appended to the relevant parameter's description.
*   **Method Body:** It writes the internal logic to validate inputs, call the `core` command, and handle return values. For action-only commands, it generates efficient code that **returns `None`** and discards the redundant success response, reinforcing an exception-based error handling pattern.

---

#### **5. Value and Benefits**

*   **Superior Developer Experience:** The `UnifiedApi`'s namespaced structure (`api.tapir.elements`) makes it clean, predictable, and discoverable.
*   **Automation & Maintainability:** The multi-stage pipeline eliminates manual work, and its intermediate artifacts make the system easy to debug, extend, and maintain.
*   **Consistency:** Provides a unified look and feel for two different APIs.
*   **Multi-Layered Type Safety:** Offers both static analysis (`TypedDicts`) and a fully runtime-validated interface (`UnifiedApi`).
*   **Predictable Error Handling:** The explicit `Raises` section in every docstring creates a clear and reliable contract for developers.
*   **Strictness and Reliability:** The mandatory use of a strict `APIModel` base class provides strong guarantees against unexpected API data.

---

Excellent. That's a much clearer and more actionable roadmap. You're right to separate the immediate, concrete tasks from the long-term vision.

I have updated the "Next Steps" section of the project brief to reflect these precise priorities.

---

#### **6. Next Steps**

The current pipeline is robust and delivers a high-quality client library. The immediate next steps are focused on improving the generated code's readability, ensuring its quality through formatting and testing, and completing the full generation-validation cycle.

##### **Immediate Priorities**

1.  **Implement Result Alias Simplification:**
    *   **Task:** Enhance the pipeline to identify `...Result` models that are simple aliases for common types (e.g., a model that is just a wrapper for `list[ExecutionResult]`).
    *   **Implementation:**
        *   In[project_brief.md](project_brief.md) **Stage 1 (Schema Analysis)**, add logic to detect these schema patterns and add a flag (e.g., `"result_is_alias_for": "list[ExecutionResult]"`) to the `_command_details.json` metadata.
        *   In **Stage 2 (Code Generation)**, use this flag to generate cleaner, more explicit return type hints directly in the method signature (e.g., `-> list[ExecutionResult]`) instead of the redundant alias name.

2.  **Integrate an Automated Formatting Step:**
    *   **Task:** Add a final stage to the overall pipeline that automatically formats all generated Python files.
    *   **Implementation:** Create a script that executes `ruff format` on the output directories of the model generation and `UnifiedApi` generation pipelines. This will ensure all generated code is clean, consistent, and compliant with project standards without complicating the generator logic.

3.  **Generate and Execute the Validation Test Suite:**
    *   **Task:** Implement the generation of the symmetric runtime validation test suite.
    *   **Implementation:** Create a script that reads the master JSON schemas and generates a `pytest` file. For each command model, this test will use `hypothesis-jsonschema` to create valid data payloads and then assert that:
        1.  The data passes validation by the corresponding Pydantic model (`models.{ModelName}.model_validate(data)`).
        2.  The data passes a static-like check with the corresponding TypedDict using `typeguard.check_type`.
    This guarantees that the Pydantic models and TypedDicts are perfectly synchronized with the source schema.

##### **Future Enhancements (Long-Term Vision)**

1.  **Expand `UnifiedApi` with Convenience Methods:** Once the generated base is fully tested and stable, explore opportunities for adding higher-level, handcrafted methods to the `UnifiedApi`. These would encapsulate common workflows or combine multiple low-level API calls into a single, powerful function (e.g., a method to get all walls on a specific story and then retrieve their properties).

2.  **Continuous Pipeline Improvement:** Continue to monitor the output of the code generators and the source schemas for any new artifacts or changes. The validation test suite will be crucial for catching regressions and ensuring the pipeline remains stable and reliable over time.