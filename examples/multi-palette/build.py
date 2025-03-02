import subprocess
import os
import shutil


def clean_build_and_dist():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folders_to_delete = ["build", "dist"]

    for folder in folders_to_delete:
        folder_path = os.path.join(script_dir, folder)
        # Check if the directory exists
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            print(f"Deleting: {folder_path}")
            shutil.rmtree(folder_path)
        else:
            print(f"Skipping: {folder_path} (not found or not a directory)")


def copy_assets_to_dist():
    # Get the current script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Define source and destination paths
    source_folder = os.path.join(script_dir, "assets")
    destination_folder = os.path.join(script_dir, r"dist\Multi-palette")

    if os.path.exists(source_folder) and os.path.isdir(source_folder):
        # Ensure the destination folder exists
        os.makedirs(destination_folder, exist_ok=True)
        print(f"Copying assets from {source_folder} to {destination_folder}")
        shutil.copytree(source_folder, os.path.join(destination_folder, "assets"), dirs_exist_ok=True)
    else:
        print(f"Source folder {source_folder} does not exist. Nothing to copy.")

cmd = [
    'nicegui-pack',
    'app.py', # your main file with ui.run()
    '--name', 'Multi-palette', # name of your app
    '--windowed', # prevent console appearing, only use with ui.run(native=True, ...)
    '--add-data', r'.venv\lib\site-packages\archicad:archicad',
    '--add-data', r'.venv\lib\site-packages\multiconn_archicad:multiconn_archicad',
    '--add-data', 'logic;logic',
    '--add-data', 'assets:assets',
    '--add-data', 'assets:.'
]


if __name__ == "__main__":
    clean_build_and_dist()
    subprocess.call(cmd)
    copy_assets_to_dist()






