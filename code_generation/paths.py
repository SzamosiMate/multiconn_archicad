import pathlib

class PipelinePaths:
    """
    A central class to hold all file and directory paths for the generation pipeline.
    Edit these paths to change the structure of the project's inputs and outputs.
    """

    # --- Source URLs ---
    COMMAND_DEFS_URL = "https://raw.githubusercontent.com/ENZYME-APD/tapir-archicad-automation/main/docs/archicad-addon/command_definitions.js"
    COMMON_SCHEMA_URL = "https://raw.githubusercontent.com/ENZYME-APD/tapir-archicad-automation/main/docs/archicad-addon/common_schema_definitions.js"

    # --- Base Directories ---
    # These directories store intermediate and final artifacts.
    SCHEMA_DIR = pathlib.Path("../schema")
    TEMP_MODELS_DIR = pathlib.Path("../temp_models")
    FINAL_SRC_DIR = pathlib.Path("../../src/multiconn_archicad")

    # --- Final Output Directories ---
    # These are derived from the base directories.
    FINAL_MODELS_DIR = FINAL_SRC_DIR / "models" / "tapir"
    FINAL_DICTS_DIR = FINAL_SRC_DIR / "dicts" / "tapir"
    FINAL_CORE_DIR = FINAL_SRC_DIR / "core"

    # --- Schema & Name List Outputs (Intermediate) ---
    MASTER_SCHEMA_OUTPUT = SCHEMA_DIR / "tapir_master_schema.json"
    BASE_MODEL_NAMES_OUTPUT = SCHEMA_DIR / "_base_model_names.json"
    COMMAND_MODELS_NAMES_OUTPUT = SCHEMA_DIR / "_command_model_names.json"
    COMMAND_DETAILS_OUTPUT = SCHEMA_DIR / "_command_details.json"

    # --- Raw Generated Files (Intermediate) ---
    RAW_PYDANTIC_MODELS = TEMP_MODELS_DIR / "input_base_models.py"
    RAW_TYPED_DICTS = TEMP_MODELS_DIR / "input_typed_dicts.py"

    # --- Cleaned Generated Files (Intermediate) ---
    CLEANED_PYDANTIC_MODELS = TEMP_MODELS_DIR / "base_models.py"
    CLEANED_TYPED_DICTS = TEMP_MODELS_DIR / "typed_dicts.py"

    # --- Final Library File Outputs ---
    FINAL_LITERAL_COMMANDS = FINAL_CORE_DIR / "literal_commands.py"
    FINAL_PYDANTIC_TYPES = FINAL_MODELS_DIR / "types.py"
    FINAL_PYDANTIC_COMMANDS = FINAL_MODELS_DIR / "commands.py"
    FINAL_TYPED_DICT_TYPES = FINAL_DICTS_DIR / "types.py"
    FINAL_TYPED_DICT_COMMANDS = FINAL_DICTS_DIR / "commands.py"

    # --- Tests ---
    TESTS_DIR = pathlib.Path("../../tests")
    GENERATED_TESTS_OUTPUT = TESTS_DIR / "test_generated_models.py"

    @classmethod
    def create_directories(cls):
        """Creates all necessary output directories for the pipeline to run."""
        print("Creating necessary output directories...")
        cls.SCHEMA_DIR.mkdir(exist_ok=True)
        cls.TEMP_MODELS_DIR.mkdir(exist_ok=True)
        cls.FINAL_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        cls.FINAL_DICTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.FINAL_CORE_DIR.mkdir(parents=True, exist_ok=True)
        print("Directories created successfully.\n")

paths = PipelinePaths()