import os
import platform
from tree_sitter import Language, Parser

# Determine the correct shared library path based on OS
PLATFORM = platform.system().lower()
if PLATFORM == 'windows':
    LIB_PATH = os.path.join(os.path.dirname(__file__), '..', 'prebuilt', 'windows-latest', 'my-languages.dll')
elif PLATFORM == 'darwin':
    LIB_PATH = os.path.join(os.path.dirname(__file__), '..', 'prebuilt', 'macos-latest', 'my-languages.dylib')
else:
    LIB_PATH = os.path.join(os.path.dirname(__file__), '..', 'prebuilt', 'ubuntu-latest', 'my-languages.so')

LIB_PATH = os.path.abspath(LIB_PATH)

# Load the TSX grammar from the shared library
TSX_LANGUAGE = Language(LIB_PATH, 'tsx')
parser = Parser()
parser.set_language(TSX_LANGUAGE)

def parse_jsx_with_treesitter(file_path: str) -> dict:
    """Parse JSX/TSX file using tree-sitter and return AST as dict."""
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    tree = parser.parse(bytes(code, 'utf-8'))
    root_node = tree.root_node

    def node_to_dict(node):
        return {
            'type': node.type,
            'start_point': node.start_point,
            'end_point': node.end_point,
            'children': [node_to_dict(child) for child in node.children] if node.children else [],
            'text': code[node.start_byte:node.end_byte] if node.child_count == 0 else None
        }

    return node_to_dict(root_node)
