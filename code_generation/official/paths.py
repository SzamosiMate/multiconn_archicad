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

    # --- Intermediate Outputs ---
    MASTER_SCHEMA_OUTPUT = SCHEMA_DIR / "official_api_master_schema.json"
    BASE_MODEL_NAMES_OUTPUT = SCHEMA_DIR / "_base_model_names.json"
    COMMAND_MODELS_NAMES_OUTPUT = SCHEMA_DIR / "_command_model_names.json"
    COMMAND_DETAILS_OUTPUT = SCHEMA_DIR / "_command_details.json"

    # --- Raw Generated Files (Intermediate) ---
    RAW_PYDANTIC_MODELS = TEMP_MODELS_DIR / "input_base_models.py"
    RAW_TYPED_DICTS = TEMP_MODELS_DIR / "input_typed_dicts.py"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    @classmethod
    def create_directories(cls):
        """Creates all necessary output directories for the crawler."""
        cls.BASE_SCHEMA_DIR.mkdir(exist_ok=True)
        cls.SCHEMA_DIR.mkdir(exist_ok=True)
        cls.TEMP_MODELS_DIR.mkdir(exist_ok=True)

official_paths = OfficialApiPaths()
