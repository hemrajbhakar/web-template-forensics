import os
import platform
import subprocess

PLATFORM = platform.system().lower()
wheel_map = {
    'windows': 'tree_sitter-0.20.1-cp311-cp311-win_amd64.whl',
    'linux':   'tree_sitter-0.20.1-cp311-cp311-linux_x86_64.whl',
    'darwin':  'tree_sitter-0.20.1-cp311-cp311-macosx_10_9_universal2.whl',
}

wheel_file = wheel_map.get(PLATFORM)
wheel_path = os.path.abspath(os.path.join('wheels', wheel_file))

if os.path.exists(wheel_path):
    subprocess.run(['pip', 'install', wheel_path])
else:
    raise FileNotFoundError(f'Wheel for platform {PLATFORM} not found at {wheel_path}')
