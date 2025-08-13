### **Project Brief: Unified Archicad API Model Generation Pipeline**

#### **1. Objective**

To automate the creation of a high-quality, consistent, and type-safe Python library for interacting with **both** the community-driven **Tapir API** and the **Official Archicad JSON API**. The primary goal is to provide a superior developer experience by transforming complex, fragmented JSON schemas into clean, predictable, and easy-to-use Pydantic models and TypedDicts.

---

#### **2. The Core Problem**

Directly using the Archicad JSON APIs in Python is challenging for several reasons:
*   **Schema Fragmentation:** The API definitions are spread across multiple files (JavaScript variables for Tapir, dozens of individual JSON files for the Official API).
*   **Schema Complexity:** The schemas contain complex structures, including recursive definitions, conditional types (`oneOf`), and inconsistent naming, which are not directly usable.
*   **Generator Artifacts:** Standard code generation tools like `datamodel-codegen`, while powerful, produce verbose and un-pythonic code with numerous artifacts (e.g., meaningless wrapper classes, `RootModel` unions, inconsistent constrained types) that need to be cleaned.

This project solves these problems by creating an automated pipeline that ingests the raw schemas and outputs pristine, developer-friendly Python models.

---

#### **3. Solution Overview: A Dual-Track Pipeline**

The solution is a robust, multi-stage pipeline composed of **two parallel tracks**—one for each API—that converge on a unified output structure. This architecture allows each track to handle the unique challenges of its source schema while ensuring the final models feel consistent and cohesive.

**Key Deliverables:**

*   **Pydantic Models:** For runtime validation and data parsing (`models/tapir/` & `models/official/`).
*   **TypedDicts:** For lightweight static analysis and type hinting (`dicts/tapir/` & `dicts/official/`).
*   **Command Metadata:** Structured JSON files detailing command names, groups, and descriptions (`_command_details.json`).
*   **Command Literals:** `literal_commands.py` files providing `Literal` types for all command names, enabling autocomplete and static error checking.
*   **Automated Tests:** A generated test suite that uses property-based testing (`hypothesis`) to validate the instantiation of all Pydantic models from their schemas.

---

#### **4. Pipeline Architecture**

The project consists of two distinct but philosophically similar pipelines:

##### **Track 1: Tapir API Pipeline**

This track processes schemas defined within JavaScript files.

1.  **Fetch Schemas:** Downloads `common_schema_definitions.js` and `command_definitions.js` from the Tapir GitHub repository.
2.  **Parse JS:** Extracts JSON-like objects from JavaScript `var` assignments.
3.  **Generate Master Schema:** Merges common and command definitions into a single, self-contained `tapir_master_schema.json`.
4.  **Generate Code:** Uses `datamodel-codegen` to create raw Pydantic models and TypedDicts from the master schema.
5.  **Surgical Cleaning:** A dedicated cleaner script (`03_model_cleaner.py`) performs targeted fixes unique to the Tapir schemas, such as:
    *   Replacing the problematic `PropertyDefaultValue` `RootModel` with a clean `TypeAlias`.
    *   Normalizing `constr` types to `str` for consistency.
6.  **Split Models:** A splitter script (`04_split_models.py`) intelligently separates the cleaned file into `types.py` (base models) and `commands.py` (command-specific models), automatically generating the necessary cross-file imports.
7.  **Generate Literals:** Creates `literal_commands.py` for full command name type safety.

##### **Track 2: Official Archicad API Pipeline**

This track is designed to handle a large number of distributed, inter-dependent JSON files.

1.  **Crawl Schemas:** A crawler (`01_crawl_site.py`) starts with `menutree.json`, recursively discovers all referenced `.json` schema files from the official documentation site, and downloads them.
2.  **Generate Master Schema:** A second script (`02_generate_master_schema.py`) reads all downloaded files, intelligently renames generic definitions (e.g., `command_parameters` -> `CreateLayoutParameters`), and merges them into a single `official_api_master_schema.json`.
3.  **Generate Code:** Uses `datamodel-codegen` with the `--use-annotated` flag to produce modern, metadata-rich Pydantic models.
4.  **Surgical Cleaning:** A highly sophisticated cleaner (`05_model_cleaner.py`) applies a series of targeted fixes to address the specific artifacts of the Official API schemas:
    *   **Systematic Wrapper Renaming (Critical):** The Archicad API frequently uses a `{ "key": { ... } }` wrapping structure. This is an **essential part of the schema**, not a generator artifact. However, `datamodel-codegen` produces non-intuitive names for these required wrapper classes (e.g., `NavigatorItemId1`, `PropertyValueOrErrorItem1`). The cleaner **renames** these classes to a consistent, readable convention (e.g., `NavigatorItemIdWrapperItem`, `PropertyValueWrapperItem`). This preserves schema validity while dramatically improving developer experience.
    *   **`oneOf` Handling (Surgical):** Replaces the generated mess for `RenameNavigatorItemParameters` with three well-named Pydantic classes (`RenameNavigatorItemByName`, `ById`, `ByNameAndId`) and a clean `TypeAlias` union, preserving all `Annotated` metadata.
    *   **`RootModel` Conversion (General):** Converts all remaining `RootModel` classes into clean `TypeAlias` definitions for better type hinting and usability.
    *   **Exception-Based Unwrapping (Surgical):** In rare cases, the generator creates *truly* redundant wrappers. The cleaner surgically unwraps the `DashOrLineItem` union to remove these useless intermediate classes, simplifying `List[DashOrLineItem1 | DashOrLineItem2]` to the more direct `List[DashItem | LineItem]`.
5.  **Split Models:** A splitter script (`06_split_models.py`), now aware of the cleaner's renaming rules, intelligently separates the cleaned models into `types.py` and `commands.py`, generating correct cross-file imports.

---

#### **5. Value and Benefits**

*   **Automation:** Eliminates hundreds of hours of manual work and ensures models can be updated easily as the APIs evolve.
*   **Consistency:** Provides a unified look and feel for models from two different APIs, significantly improving the developer experience.
*   **Type Safety:** Enables powerful static analysis and IDE autocompletion, catching bugs before runtime.
*   **Maintainability:** The pipeline is modular and well-documented, making it easy to understand, debug, and extend.
*   **Robustness:** The "surgical cleaning" steps demonstrate an advanced understanding of the problem space, producing a result far superior to what code generators can achieve alone.