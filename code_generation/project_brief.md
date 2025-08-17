### **Project Brief: Unified Archicad API Model Generation Pipeline **

#### **1. Objective**

To automate the creation of a high-quality, consistent, and type-safe Python library for interacting with **both** the community-driven **Tapir API** and the **Official Archicad JSON API**. The primary goal is to provide a superior developer experience by transforming complex, fragmented JSON schemas into clean, predictable, and easy-to-use Pydantic models and TypedDicts.

---

#### **2. The Core Problem**

Directly using the Archicad JSON APIs in Python is challenging for several reasons:
*   **Schema Fragmentation:** The API definitions are spread across multiple files (JavaScript variables for Tapir, dozens of individual JSON files for the Official API).
*   **Schema Complexity:** The schemas contain complex structures, including recursive definitions, conditional types (`oneOf`), and inconsistent naming, which are not directly usable.
*   **Generator Artifacts:** Standard code generation tools like `datamodel-codegen`, while powerful, produce verbose and un-pythonic code with numerous artifacts that need to be cleaned. These include meaningless wrapper classes, `RootModel` unions, keyword collisions (`copy` -> `copy_`), and boilerplate configurations.

This project solves these problems by creating an automated pipeline that ingests the raw schemas and outputs pristine, developer-friendly Python models.

---

#### **3. Solution Overview: A Dual-Track Pipeline**

The solution is a robust, multi-stage pipeline composed of **two parallel tracks**—one for each API—that converge on a unified output structure. This architecture allows each track to handle the unique challenges of its source schema while ensuring the final models feel consistent and cohesive.

**Key Deliverables:**

*   **Pydantic Models:** For runtime validation and data parsing, built with modern `Annotated` types (`models/tapir/` & `models/official/`).
*   **TypedDicts:** For lightweight static analysis and type hinting (`dicts/tapir/` & `dicts/official/`).
*   **Command Metadata:** Structured JSON files detailing command names, groups, and descriptions (`_command_details.json`).
*   **Command Literals:** `literal_commands.py` files providing `Literal` types for all command names, enabling autocomplete and static error checking.
*   **Symmetric Runtime Validation Suite:** A unified, auto-generated test suite that performs **symmetric runtime validation** for both Pydantic models and TypedDicts. Using `hypothesis` to generate schema-compliant data, it confirms that Pydantic models can parse the data and, simultaneously, uses `typeguard` to verify that the same data conforms to the strict shape of the corresponding `TypedDict`.

---

#### **4. Pipeline Architecture**

The project consists of two distinct but philosophically similar pipelines:

##### **Track 1: Tapir API Pipeline**

This track now mirrors the modern approach of the Official pipeline.

1.  **Fetch & Parse:** Downloads and extracts JSON-like objects from the Tapir JS files.
2.  **Generate Master Schema:** Merges common and command definitions into a single, self-contained `tapir_master_schema.json`.
3.  **Generate Code:** Uses `datamodel-codegen` with modern flags (`--use-annotated`, `--field-constraints`) to produce Pydantic v2 models and TypedDicts.
4.  **Surgical Cleaning (Pydantic):** A minimal but essential cleaner script (`03_model_cleaner.py`) performs targeted fixes, such as removing the boilerplate top-level `RootModel` (`TapirMasterModels`) created by the generator.
5.  **Surgical Cleaning (TypedDict):** A dedicated cleaner (`06_typed_dict_cleaner.py`) corrects generator artifacts like keyword collisions (`copy` -> `copy_`).
6.  **Split Models:** Intelligent splitter scripts (`04_...`, `07_...`) separate the cleaned files into `types.py` and `commands.py`, automatically generating the necessary cross-file imports.
7.  **Generate Literals:** Creates `literal_commands.py` for full command name type safety.

##### **Track 2: Official Archicad API Pipeline**

This track is designed to handle a large number of distributed, inter-dependent JSON files.

1.  **Crawl Schemas:** A crawler (`01_crawl_site.py`) recursively discovers and downloads all `.json` schema files from the official documentation site.
2.  **Generate Master Schema:** A script (`02_generate_master_schema.py`) reads all downloaded files, intelligently renames generic definitions, and merges them into a single `official_api_master_schema.json`.
3.  **Generate Code:** Uses `datamodel-codegen` with the same modern flags to produce `Annotated` Pydantic models and TypedDicts.
4.  **Surgical Cleaning:** A highly sophisticated cleaner (`05_model_cleaner.py`) applies a series of targeted fixes:
    *   **Systematic Wrapper Renaming (Critical):** The Archicad API frequently uses a `{ "key": { ... } }` wrapping structure. This is an **essential part of the schema**. The cleaner **renames** the generator's non-intuitive class names (e.g., `NavigatorItemId1`) to a consistent, readable convention (e.g., `NavigatorItemIdWrapperItem`), preserving schema validity while dramatically improving developer experience.
    *   **Complex `oneOf` Handling:** Replaces messy generated unions (like for `RenameNavigatorItemParameters`) with well-named Pydantic classes and a clean `RootModel` or `TypeAlias` wrapper, preserving all metadata.
    *   **General `RootModel` Conversion:** Converts simple `RootModel` unions into clean `TypeAlias` definitions for better type hinting.
5.  **Split Models:** A splitter script (`06_split_models.py`) intelligently separates the cleaned models into `types.py` and `commands.py`.
6.  **Unified Testing Strategy:** Both pipelines feed into a single, auto-generated test suite (`07_generate_model_tests.py` and `08_generate_model_tests.py` for Tapir) that uses **`typeguard`** for robust, symmetric runtime validation of both Pydantic models and TypedDicts, ensuring they remain perfectly in sync with the source schemas.

---

#### **5. Value and Benefits**

*   **Automation:** Eliminates hundreds of hours of manual work and ensures models can be easily updated.
*   **Consistency:** Provides a unified look and feel for models from two different APIs.
*   **Type Safety:** Enables powerful static analysis and IDE autocompletion, catching bugs before runtime.
*   **Runtime Guarantees for Static Types:** By integrating `typeguard`, the pipeline provides runtime validation for `TypedDict`s, a unique feature that bridges the gap between static analysis and real-world data validation, ensuring a higher degree of reliability.
*   **Maintainability:** The pipeline is modular and well-documented, making it easy to debug and extend.
*   **Robustness:** The "surgical cleaning" steps demonstrate an advanced understanding of the problem space, producing a result far superior to what code generators can achieve alone.

---

#### **6. Next Steps & Known Issues**

The current pipeline is robust, but the following tasks are planned to further improve model quality and consistency:

1.  **Handling `additionalProperties`:** Investigate schemas that use `additionalProperties: true`.
    *   For the **Official API's `ExecuteAddOnCommand`**, this is a required feature to support dynamic parameters. The models need to be configured to allow this explicitly.
    *   For the **Tapir API**, this appears to be a schema error that allows `hypothesis` to generate invalid data (e.g., objects with an empty string key). The plan is to fix the schema upstream and submit a pull request to the Tapir repository.

2.  **Implement a Global `StrictBaseModel`:** To enforce strict validation (`extra='forbid'`) consistently across all models and remove verbose `ConfigDict` blocks, a shared `StrictBaseModel` will be implemented. This is linked to the `additionalProperties` investigation and will ensure all models correctly reject unexpected fields by default, unless explicitly designed to allow them.