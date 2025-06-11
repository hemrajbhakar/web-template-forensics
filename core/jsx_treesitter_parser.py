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

def parse_jsx_with_treesitter(file_path: str):
    """Parse JSX/TSX file using tree-sitter, return normalized AST and call graph."""
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    tree = parser.parse(bytes(code, 'utf-8'))
    root_node = tree.root_node

    id_map = {}
    lit_map = {}
    call_graph = {}
    function_stack = []
    anon_func_counter = [0]

    def normalize_node(node):
        # Normalize identifiers
        if node.type == 'identifier':
            name = node.text.decode('utf-8')
            if name not in id_map:
                id_map[name] = f'id{len(id_map)}'
            return {'type': 'identifier', 'name': id_map[name]}
        # Normalize literals
        if node.type in ('string', 'string_literal', 'number', 'number_literal', 'true', 'false', 'boolean'):
            lit_key = node.text.decode('utf-8')
            if lit_key not in lit_map:
                lit_map[lit_key] = f'lit{len(lit_map)}'
            return {'type': node.type, 'value': lit_map[lit_key]}
        # Function/component definitions
        if node.type in ('function_declaration', 'function_expression', 'arrow_function', 'method_definition'):  # covers most cases
            func_name = get_function_name(node) or f"anon_func_{anon_func_counter[0]}"
            if not get_function_name(node):
                anon_func_counter[0] += 1
            function_stack.append(func_name)
            call_graph.setdefault(func_name, set())
            children = [normalize_node(child) for child in node.children]
            function_stack.pop()
            return {'type': node.type, 'name': func_name, 'children': children}
        # Call expressions
        if node.type == 'call_expression':
            callee = get_callee_name(node)
            if function_stack and callee:
                call_graph[function_stack[-1]].add(callee)
            children = [normalize_node(child) for child in node.children]
            return {'type': node.type, 'callee': callee, 'children': children}
        # Default: recurse
        return {
            'type': node.type,
            'children': [normalize_node(child) for child in node.children] if node.children else [],
            'text': code[node.start_byte:node.end_byte] if node.child_count == 0 else None
        }

    def get_function_name(node):
        # Try to extract function or method name
        name_node = node.child_by_field_name('name')
        if name_node:
            return name_node.text.decode('utf-8')
        return None

    def get_callee_name(node):
        # Try to extract callee name from call_expression
        for child in node.children:
            if child.type == 'identifier':
                return id_map.get(child.text.decode('utf-8'), child.text.decode('utf-8'))
            # For member_expression, get property name
            if child.type == 'member_expression':
                prop = child.child_by_field_name('property')
                if prop:
                    return id_map.get(prop.text.decode('utf-8'), prop.text.decode('utf-8'))
        return None

    normalized_ast = normalize_node(root_node)
    # Convert call_graph sets to lists for JSON serialization
    call_graph_out = {k: list(v) for k, v in call_graph.items()}
    return {'ast': normalized_ast, 'call_graph': call_graph_out}

def tree_similarity(node1: dict, node2: dict) -> float:
    """Recursively compare two AST subtrees and return a similarity score between 0 and 1."""
    if not node1 and not node2:
        return 1.0
    if not node1 or not node2:
        return 0.0
    if node1.get('type') != node2.get('type'):
        return 0.0
    children1 = node1.get('children', [])
    children2 = node2.get('children', [])
    if not children1 and not children2:
        val1 = node1.get('name') or node1.get('value') or node1.get('text')
        val2 = node2.get('name') or node2.get('value') or node2.get('text')
        return 1.0 if val1 == val2 else 0.8 if (val1 is None or val2 is None) else 0.0
    matched = 0
    used2 = set()
    for c1 in children1:
        best = 0.0
        best_j = -1
        for j, c2 in enumerate(children2):
            if j in used2:
                continue
            sim = tree_similarity(c1, c2)
            if sim > best:
                best = sim
                best_j = j
        if best_j >= 0:
            used2.add(best_j)
        matched += best
    total = max(len(children1), len(children2))
    return matched / total if total else 1.0
