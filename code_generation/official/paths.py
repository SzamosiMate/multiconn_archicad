import pathlib


class OfficialApiPaths:
    """
    A central class to hold all file and directory paths for the official API schema crawler.
    """

    # --- Source URL ---
    BASE_URL = "https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/content/"
    MENU_TREE_URL = f"{BASE_URL}menutree.json"

    # --- Output Directory ---
    SCHEMA_DIR = pathlib.Path("../schema")
    TEMP_MODELS_DIR = pathlib.Path("../temp_models")

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    @classmethod
    def create_directories(cls):
        """Creates all necessary output directories for the crawler."""
        cls.SCHEMA_DIR.mkdir(exist_ok=True)
        cls.TEMP_MODELS_DIR.mkdir(exist_ok=True)

official_paths = OfficialApiPaths()
