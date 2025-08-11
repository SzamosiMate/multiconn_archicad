import json
import re
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Set, Optional

from code_generation.official.paths import official_paths


def fetch_content(url: str) -> Optional[str]:
    """Fetches text content from a URL using the standard urllib library."""
    request = urllib.request.Request(url, headers=official_paths.HEADERS)
    try:
        with urllib.request.urlopen(request) as response:
            if response.status == 200:
                return response.read().decode("utf-8")
            else:
                print(f"⚠️  Failed to fetch {url}: HTTP {response.status}")
                return None
    except urllib.error.URLError as e:
        print(f"⚠️  Error fetching {url}: {e}")
        return None


def extract_schema_filenames_from_menu(menu_items: List[Dict[str, Any]]) -> Set[str]:
    """Recursively extracts all unique .json filenames from the menu tree."""
    filenames = set()
    for item in menu_items:
        if filename := item.get("commanddocumentation"):
            if filename.endswith(".json"):
                filenames.add(filename)

        if sub_items := item.get("menuitems"):
            filenames.update(extract_schema_filenames_from_menu(sub_items))
    return filenames


def find_referenced_schemas(content: str) -> Set[str]:
    """Parses content to find string literals ending in '.json'."""
    return set(re.findall(r'"([^"#]+\.json)', content))

def get_schema_file_names() -> set[str] | None:
    """ Fetch the menu to get the initial list of files. """
    print(f"➡️  Fetching menu tree from {official_paths.MENU_TREE_URL}...")
    menu_content = fetch_content(official_paths.MENU_TREE_URL)
    if not menu_content:
        print("❌ ERROR: Could not fetch menutree.json. Aborting.")
        return None
    try:
        menu_tree = json.loads(menu_content)
        files_to_process = extract_schema_filenames_from_menu(menu_tree.get("menuitems", []))
        print(f"✅ Found {len(files_to_process)} initial schema files.")
        return files_to_process
    except json.JSONDecodeError:
        print("❌ ERROR: Could not parse menutree.json as JSON. Aborting.")
        return None

def process_files(files_to_process) -> None:
    """ Process the queue of files to download. """
    processed_files: Set[str] = set()
    while files_to_process:
        filename = files_to_process.pop()
        if filename in processed_files:
            continue

        print(f"⬇️  Processing {filename}...")
        file_url = f"{official_paths.BASE_URL}{filename}"
        content = fetch_content(file_url)

        if content:
            local_path = official_paths.SCHEMA_DIR / filename
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(content, encoding="utf-8")
            processed_files.add(filename)

            # Add any newly discovered schema files to the queue.
            for new_file in find_referenced_schemas(content):
                if new_file not in processed_files:
                    files_to_process.add(new_file)

        time.sleep(0.1)  # Be polite to the server.

    print(f"\n🎉 Crawl complete! Downloaded {len(processed_files)} total files.")
    print(f"📂 Schemas are saved in ./{official_paths.SCHEMA_DIR}/")


def run_crawler():
    """Orchestrates the schema crawling and downloading process."""
    print("--- Starting Official Archicad Schema Crawl ---")
    official_paths.create_directories()
    files_to_process = get_schema_file_names()
    process_files(files_to_process)

if __name__ == "__main__":
    run_crawler()