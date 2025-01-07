import subprocess



cmd = [
    'nicegui-pack',
    'app.py', # your main file with ui.run()
    '--name', 'Multi-palette', # name of your app
    '--windowed', # prevent console appearing, only use with ui.run(native=True, ...)
    '--add-data', r'.venv\lib\site-packages\archicad:archicad',
    '--add-data', 'assets:assets',
    '--add-data', 'assets:.'
]
subprocess.call(cmd)


