import pathlib


class OfficialApiPaths:
    """
    A central class to hold all file and directory paths for the official API schema crawler.
    """

    # --- Source URL ---
    BASE_URL = "https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/content/"
    MENU_TREE_URL = f"{BASE_URL}menutree.json"

    # --- Output Directory ---
    BASE_SCHEMA_DIR = pathlib.Path("../base_schema")
    SCHEMA_DIR = pathlib.Path("../schema")
    TEMP_MODELS_DIR = pathlib.Path("../temp_models")

    FINAL_SRC_DIR = pathlib.Path("../../../src/multiconn_archicad")
    FINAL_MODELS_DIR = FINAL_SRC_DIR / "models" / "official"
    FINAL_DICTS_DIR = FINAL_SRC_DIR / "dicts" / "official"

    # --- Intermediate Outputs ---
    MASTER_SCHEMA_OUTPUT = SCHEMA_DIR / "official_api_master_schema.json"
    BASE_MODEL_NAMES_OUTPUT = SCHEMA_DIR / "_base_model_names.json"
    COMMAND_MODELS_NAMES_OUTPUT = SCHEMA_DIR / "_command_model_names.json"
    COMMAND_DETAILS_OUTPUT = SCHEMA_DIR / "_command_details.json"

    # --- Raw Generated Files (Intermediate) ---
    RAW_PYDANTIC_MODELS = TEMP_MODELS_DIR / "input_base_models.py"
    RAW_TYPED_DICTS = TEMP_MODELS_DIR / "input_typed_dicts.py"

    # --- Clean Generated Files (Intermediate) ---
    CLEANED_PYDANTIC_MODELS = TEMP_MODELS_DIR / "cleaned_base_models.py"
    CONVERTED_PYDANTIC_MODELS = TEMP_MODELS_DIR / "annotated_models.py"
    CLEANED_TYPED_DICTS = TEMP_MODELS_DIR / "cleaned_typed_dicts.py"

    FINAL_PYDANTIC_TYPES = FINAL_MODELS_DIR / "types.py"
    FINAL_PYDANTIC_COMMANDS = FINAL_MODELS_DIR / "commands.py"
    FINAL_TYPED_DICT_TYPES = FINAL_DICTS_DIR / "types.py"
    FINAL_TYPED_DICT_COMMANDS = FINAL_DICTS_DIR / "commands.py"

    # --- Tests ---
    TESTS_DIR = pathlib.Path("../../../tests")
    GENERATED_TESTS_OUTPUT = TESTS_DIR / "test_generated_official_models.py"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    @classmethod
    def create_directories(cls):
        """Creates all necessary output directories for the crawler."""
        cls.BASE_SCHEMA_DIR.mkdir(exist_ok=True)
        cls.SCHEMA_DIR.mkdir(exist_ok=True)
        cls.TEMP_MODELS_DIR.mkdir(exist_ok=True)
        cls.FINAL_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        cls.FINAL_DICTS_DIR.mkdir(parents=True, exist_ok=True)

official_paths = OfficialApiPaths()
