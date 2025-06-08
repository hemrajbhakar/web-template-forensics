def parse_jsx_with_treesitter(file_path: str) -> dict:
    """Parse JSX/TSX file using the Node.js tree-sitter parser and return AST as dict."""
    import subprocess, json, os
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='r+', encoding='utf-8') as ast_file:
        ast_file_path = ast_file.name
    result = subprocess.run([
        'node', os.path.abspath('jsx_parser.js'), os.path.abspath(file_path), ast_file_path
    ], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"JSX parser error: {result.stderr}")
        return {}
    with open(ast_file_path, 'r', encoding='utf-8') as f:
        ast = json.load(f)
    return ast 