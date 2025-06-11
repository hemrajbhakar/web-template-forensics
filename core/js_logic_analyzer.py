"""
JavaScript/TypeScript Logic Analyzer
Analyzes and compares JavaScript/TypeScript code logic similarity.
"""

import os
from typing import Dict, List, Tuple, Optional, Any
from tree_sitter import Language, Parser
import platform
from collections import defaultdict, Counter
import difflib
import re
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class JSLogicAnalyzer:
    def __init__(self):
        try:
            # Determine the correct shared library path based on OS
            PLATFORM = platform.system().lower()
            if PLATFORM == 'windows':
                LIB_PATH = os.path.join(os.path.dirname(__file__), '..', 'prebuilt', 'windows-latest', 'my-languages.dll')
            elif PLATFORM == 'darwin':
                LIB_PATH = os.path.join(os.path.dirname(__file__), '..', 'prebuilt', 'macos-latest', 'my-languages.dylib')
            else:
                LIB_PATH = os.path.join(os.path.dirname(__file__), '..', 'prebuilt', 'ubuntu-latest', 'my-languages.so')

            LIB_PATH = os.path.abspath(LIB_PATH)
            logger.debug(f"Loading tree-sitter library from: {LIB_PATH}")
            
            if not os.path.exists(LIB_PATH):
                raise FileNotFoundError(f"Tree-sitter library not found at: {LIB_PATH}")
            
            # Load the JavaScript and TypeScript grammars
            self.JS_LANGUAGE = Language(LIB_PATH, 'javascript')
            self.TS_LANGUAGE = Language(LIB_PATH, 'typescript')
            
            # Initialize parsers
            self.js_parser = Parser()
            self.js_parser.set_language(self.JS_LANGUAGE)
            self.ts_parser = Parser()
            self.ts_parser.set_language(self.TS_LANGUAGE)
            
            logger.debug("Successfully initialized JSLogicAnalyzer")
        except Exception as e:
            logger.error(f"Error initializing JSLogicAnalyzer: {str(e)}", exc_info=True)
            raise

    def parse_file(self, file_path: str) -> Dict:
        """Parse JS/TS file using tree-sitter and return normalized AST and call graph."""
        try:
            logger.debug(f"Parsing file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            ext = os.path.splitext(file_path)[1].lower()
            parser = self.ts_parser if ext == '.ts' else self.js_parser
            tree = parser.parse(bytes(code, 'utf-8'))
            if not tree:
                logger.warning(f"Parser returned no tree for file: {file_path}")
                return {}
            # Extract normalized AST and call graph
            ast, call_graph = self._normalize_ast_with_call_graph(tree.root_node, code)
            logger.debug(f"Successfully parsed file: {file_path}")
            return {'ast': ast, 'call_graph': call_graph}
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {str(e)}", exc_info=True)
            return {}

    def _normalize_ast_with_call_graph(self, node: Any, code: str, id_map=None, lit_map=None, id_counter=None, lit_counter=None, call_graph=None, function_stack=None, anon_func_counter=None):
        """Normalize AST and extract call graph (function -> called functions)."""
        if id_map is None:
            id_map = {}
        if lit_map is None:
            lit_map = {}
        if id_counter is None:
            id_counter = {'id': 0}
        if lit_counter is None:
            lit_counter = {'lit': 0}
        if call_graph is None:
            call_graph = {}
        if function_stack is None:
            function_stack = []
        if anon_func_counter is None:
            anon_func_counter = [0]
        if not node:
            return {}, call_graph
        # Normalize identifiers
        if node.type == 'identifier':
            name = node.text.decode('utf-8')
            if name not in id_map:
                id_map[name] = f'id{len(id_map)}'
            return {'type': 'identifier', 'name': id_map[name]}, call_graph
        # Normalize literals
        if node.type in ('string', 'string_literal', 'number', 'number_literal', 'true', 'false', 'boolean'):
            lit_key = node.text.decode('utf-8')
            if lit_key not in lit_map:
                lit_map[lit_key] = f'lit{len(lit_map)}'
            return {'type': node.type, 'value': lit_map[lit_key]}, call_graph
        # Function definitions
        if node.type in ('function_declaration', 'function_expression', 'arrow_function', 'method_definition'):
            func_name = self._get_node_name(node) or f"anon_func_{anon_func_counter[0]}"
            if not self._get_node_name(node):
                anon_func_counter[0] += 1
            function_stack.append(func_name)
            call_graph.setdefault(func_name, set())
            children = []
            for child in node.children:
                norm_child, call_graph = self._normalize_ast_with_call_graph(child, code, id_map, lit_map, id_counter, lit_counter, call_graph, function_stack, anon_func_counter)
                children.append(norm_child)
            function_stack.pop()
            return {'type': node.type, 'name': func_name, 'children': children}, call_graph
        # Call expressions
        if node.type == 'call_expression':
            callee = self._get_callee_name(node, id_map)
            if function_stack and callee:
                call_graph[function_stack[-1]].add(callee)
            children = []
            for child in node.children:
                norm_child, call_graph = self._normalize_ast_with_call_graph(child, code, id_map, lit_map, id_counter, lit_counter, call_graph, function_stack, anon_func_counter)
                children.append(norm_child)
            return {'type': node.type, 'callee': callee, 'children': children}, call_graph
        # Default: recurse
        children = []
        for child in node.children:
            norm_child, call_graph = self._normalize_ast_with_call_graph(child, code, id_map, lit_map, id_counter, lit_counter, call_graph, function_stack, anon_func_counter)
            children.append(norm_child)
        return {
            'type': node.type,
            'children': children,
            'text': code[node.start_byte:node.end_byte] if node.child_count == 0 else None
        }, call_graph

    def _get_callee_name(self, node: Any, id_map) -> str:
        for child in node.children:
            if child.type == 'identifier':
                return id_map.get(child.text.decode('utf-8'), child.text.decode('utf-8'))
            if child.type == 'member_expression':
                prop = child.child_by_field_name('property')
                if prop:
                    return id_map.get(prop.text.decode('utf-8'), prop.text.decode('utf-8'))
        return None

    def compare_call_graphs(self, cg1: dict, cg2: dict) -> float:
        """Compare two call graphs using Jaccard similarity of edges."""
        edges1 = set((caller, callee) for caller, callees in cg1.items() for callee in callees)
        edges2 = set((caller, callee) for caller, callees in cg2.items() for callee in callees)
        if not edges1 and not edges2:
            return 1.0
        if not edges1 or not edges2:
            return 0.0
        intersection = len(edges1 & edges2)
        union = len(edges1 | edges2)
        return intersection / union if union else 0.0

    def compare_files(self, file1: str, file2: str) -> Dict:
        """Compare two JS/TS files and return similarity analysis, including function match counts and call graph similarity."""
        parsed1 = self.parse_file(file1)
        parsed2 = self.parse_file(file2)
        tree1 = parsed1.get('ast', {})
        tree2 = parsed2.get('ast', {})
        call_graph1 = parsed1.get('call_graph', {})
        call_graph2 = parsed2.get('call_graph', {})
        # Calculate various similarity metrics
        function_similarity = self._compare_functions(tree1, tree2)
        import_similarity = self._compare_imports(tree1, tree2)
        class_similarity = self._compare_classes(tree1, tree2)
        control_flow_similarity = self._compare_control_flow(tree1, tree2)
        call_graph_similarity = self.compare_call_graphs(call_graph1, call_graph2)
        # Function-level match counts
        functions1 = self._extract_functions(tree1)
        functions2 = self._extract_functions(tree2)
        total_functions = max(len(functions1), len(functions2))
        matching_functions = 0
        different_functions = 0
        missing_functions = 0
        extra_functions = 0
        matched2 = set()
        for func1 in functions1:
            best_score = 0.0
            best_idx = -1
            for idx2, func2 in enumerate(functions2):
                sig_similarity = self._compare_function_signatures(func1, func2)
                body_similarity = self._compare_function_bodies(func1, func2)
                similarity = sig_similarity * 0.3 + body_similarity * 0.7
                if similarity > best_score:
                    best_score = similarity
                    best_idx = idx2
            if best_score > 0.8:
                matching_functions += 1
                if best_idx >= 0:
                    matched2.add(best_idx)
            elif best_score > 0.5:
                different_functions += 1
                if best_idx >= 0:
                    matched2.add(best_idx)
            else:
                missing_functions += 1
        extra_functions = len(functions2) - len(matched2)
        # Calculate overall similarity score (add call graph similarity)
        overall_similarity = (
            function_similarity * 0.35 +
            import_similarity * 0.15 +
            class_similarity * 0.15 +
            control_flow_similarity * 0.15 +
            call_graph_similarity * 0.2
        )
        return {
            'similarity': round(overall_similarity, 2),
            'details': {
                'function_similarity': round(function_similarity, 2),
                'import_similarity': round(import_similarity, 2),
                'class_similarity': round(class_similarity, 2),
                'control_flow_similarity': round(control_flow_similarity, 2),
                'call_graph_similarity': round(call_graph_similarity, 2),
                'total_functions': total_functions,
                'matching_functions': matching_functions,
                'different_functions': different_functions,
                'missing_functions': missing_functions,
                'extra_functions': extra_functions
            }
        }

    def _compare_functions(self, tree1: Dict, tree2: Dict) -> float:
        """Compare function declarations between two ASTs."""
        functions1 = self._extract_functions(tree1)
        functions2 = self._extract_functions(tree2)
        
        if not functions1 and not functions2:
            return 1.0
        if not functions1 or not functions2:
            return 0.0
            
        # Compare function signatures and bodies
        matches = 0
        total = max(len(functions1), len(functions2))
        
        for func1 in functions1:
            best_match = 0.0
            for func2 in functions2:
                # Compare function signatures
                sig_similarity = self._compare_function_signatures(func1, func2)
                # Compare function bodies
                body_similarity = self._compare_function_bodies(func1, func2)
                # Combined similarity
                similarity = sig_similarity * 0.3 + body_similarity * 0.7
                best_match = max(best_match, similarity)
            matches += best_match
            
        return matches / total

    def _extract_functions(self, tree: Dict) -> List[Dict]:
        """Extract all function declarations from AST."""
        functions = []
        def traverse(node):
            if node.get('type') in ('function_declaration', 'method_definition'):
                functions.append(node)
            for child in node.get('children', []):
                traverse(child)
        traverse(tree)
        return functions

    def _compare_function_signatures(self, func1: Dict, func2: Dict) -> float:
        """Compare function signatures (name and parameters)."""
        if func1.get('name') != func2.get('name'):
            return 0.0
            
        params1 = func1.get('parameters', [])
        params2 = func2.get('parameters', [])
        
        if len(params1) != len(params2):
            return 0.5  # Partial match if parameter count differs
            
        return 1.0  # Full match if names and parameter counts match

    def _tree_similarity(self, node1: Dict, node2: Dict) -> float:
        """Recursively compare two AST subtrees and return a similarity score between 0 and 1."""
        if not node1 and not node2:
            return 1.0
        if not node1 or not node2:
            return 0.0
        if node1.get('type') != node2.get('type'):
            return 0.0
        # Compare children recursively
        children1 = node1.get('children', [])
        children2 = node2.get('children', [])
        if not children1 and not children2:
            # Compare leaf node values if present
            val1 = node1.get('name') or node1.get('value') or node1.get('text')
            val2 = node2.get('name') or node2.get('value') or node2.get('text')
            return 1.0 if val1 == val2 else 0.8 if (val1 is None or val2 is None) else 0.0
        # Pairwise match children (greedy best match)
        matched = 0
        used2 = set()
        for c1 in children1:
            best = 0.0
            best_j = -1
            for j, c2 in enumerate(children2):
                if j in used2:
                    continue
                sim = self._tree_similarity(c1, c2)
                if sim > best:
                    best = sim
                    best_j = j
            if best_j >= 0:
                used2.add(best_j)
            matched += best
        total = max(len(children1), len(children2))
        return matched / total if total else 1.0

    def _compare_function_bodies(self, func1: Dict, func2: Dict) -> float:
        """Compare function bodies using tree-based similarity."""
        body1 = func1.get('body', {})
        body2 = func2.get('body', {})
        return self._tree_similarity(body1, body2)

    def _compare_imports(self, tree1: Dict, tree2: Dict) -> float:
        """Compare import/export statements between two ASTs."""
        imports1 = self._extract_imports(tree1)
        imports2 = self._extract_imports(tree2)
        
        if not imports1 and not imports2:
            return 1.0
        if not imports1 or not imports2:
            return 0.0
            
        # Compare import sources and specifiers
        matches = 0
        total = max(len(imports1), len(imports2))
        
        for imp1 in imports1:
            best_match = 0.0
            for imp2 in imports2:
                if imp1.get('source') == imp2.get('source'):
                    # Compare specifiers
                    spec_similarity = self._compare_import_specifiers(
                        imp1.get('specifiers', []),
                        imp2.get('specifiers', [])
                    )
                    best_match = max(best_match, spec_similarity)
            matches += best_match
            
        return matches / total

    def _extract_imports(self, tree: Dict) -> List[Dict]:
        """Extract all import/export declarations from AST."""
        imports = []
        
        def traverse(node):
            if node.get('type') in ('import_declaration', 'export_declaration'):
                imports.append(node)
            for child in node.get('children', []):
                traverse(child)
                
        traverse(tree)
        return imports

    def _compare_import_specifiers(self, spec1: List[Dict], spec2: List[Dict]) -> float:
        """Compare import/export specifiers."""
        if not spec1 and not spec2:
            return 1.0
        if not spec1 or not spec2:
            return 0.0
            
        # Compare specifier names
        names1 = {s.get('name') for s in spec1}
        names2 = {s.get('name') for s in spec2}
        
        intersection = len(names1 & names2)
        union = len(names1 | names2)
        
        return intersection / union if union else 0.0

    def _compare_classes(self, tree1: Dict, tree2: Dict) -> float:
        """Compare class declarations between two ASTs."""
        classes1 = self._extract_classes(tree1)
        classes2 = self._extract_classes(tree2)
        
        if not classes1 and not classes2:
            return 1.0
        if not classes1 or not classes2:
            return 0.0
            
        # Compare class structures and methods
        matches = 0
        total = max(len(classes1), len(classes2))
        
        for class1 in classes1:
            best_match = 0.0
            for class2 in classes2:
                if class1.get('name') == class2.get('name'):
                    # Compare methods
                    method_similarity = self._compare_class_methods(
                        class1.get('methods', []),
                        class2.get('methods', [])
                    )
                    best_match = max(best_match, method_similarity)
            matches += best_match
            
        return matches / total

    def _extract_classes(self, tree: Dict) -> List[Dict]:
        """Extract all class declarations from AST."""
        classes = []
        
        def traverse(node):
            if node.get('type') in ('class_declaration', 'class_expression'):
                classes.append(node)
            for child in node.get('children', []):
                traverse(child)
                
        traverse(tree)
        return classes

    def _compare_class_methods(self, methods1: List[Dict], methods2: List[Dict]) -> float:
        """Compare methods between two classes."""
        if not methods1 and not methods2:
            return 1.0
        if not methods1 or not methods2:
            return 0.0
            
        # Compare method signatures and bodies
        matches = 0
        total = max(len(methods1), len(methods2))
        
        for method1 in methods1:
            best_match = 0.0
            for method2 in methods2:
                if method1.get('name') == method2.get('name'):
                    # Compare method bodies
                    body_similarity = self._compare_function_bodies(method1, method2)
                    best_match = max(best_match, body_similarity)
            matches += best_match
            
        return matches / total

    def _compare_control_flow(self, tree1: Dict, tree2: Dict) -> float:
        """Compare control flow structures between two ASTs."""
        flow1 = self._extract_control_flow(tree1)
        flow2 = self._extract_control_flow(tree2)
        
        if not flow1 and not flow2:
            return 1.0
        if not flow1 or not flow2:
            return 0.0
            
        # Compare control flow structures
        matches = 0
        total = max(len(flow1), len(flow2))
        
        for node1 in flow1:
            best_match = 0.0
            for node2 in flow2:
                if node1.get('type') == node2.get('type'):
                    # Compare conditions and bodies
                    condition_similarity = self._compare_conditions(
                        node1.get('condition', {}),
                        node2.get('condition', {})
                    )
                    body_similarity = self._compare_function_bodies(
                        node1.get('body', {}),
                        node2.get('body', {})
                    )
                    similarity = condition_similarity * 0.3 + body_similarity * 0.7
                    best_match = max(best_match, similarity)
            matches += best_match
            
        return matches / total

    def _extract_control_flow(self, tree: Dict) -> List[Dict]:
        """Extract all control flow structures from AST."""
        flow_nodes = []
        
        def traverse(node):
            if node.get('type') in ('for_statement', 'while_statement', 'if_statement'):
                flow_nodes.append(node)
            for child in node.get('children', []):
                traverse(child)
                
        traverse(tree)
        return flow_nodes

    def _compare_conditions(self, cond1: Dict, cond2: Dict) -> float:
        """Compare control flow conditions."""
        str1 = str(cond1)
        str2 = str(cond2)
        return difflib.SequenceMatcher(None, str1, str2).ratio()

    def _get_node_name(self, node):
        """Robustly extract the name of a function or method node from a tree-sitter node."""
        # Try to get the name field (works for function_declaration, method_definition)
        name_node = getattr(node, 'child_by_field_name', lambda x: None)('name')
        if name_node:
            return name_node.text.decode('utf-8')
        # For function expressions or arrow functions assigned to a variable: look for parent variable declarator
        parent = getattr(node, 'parent', None)
        if parent and hasattr(parent, 'type') and parent.type == 'variable_declarator':
            id_node = parent.child_by_field_name('name')
            if id_node:
                return id_node.text.decode('utf-8')
        # For assignment expressions (e.g., foo = function() {})
        if parent and hasattr(parent, 'type') and parent.type == 'assignment_expression':
            left = parent.child_by_field_name('left')
            if left and left.type == 'identifier':
                return left.text.decode('utf-8')
        # Fallback: None
        return None 