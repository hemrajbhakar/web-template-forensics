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
        """Parse JS/TS file using tree-sitter and return normalized AST."""
        try:
            logger.debug(f"Parsing file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Choose parser based on file extension
            ext = os.path.splitext(file_path)[1].lower()
            parser = self.ts_parser if ext == '.ts' else self.js_parser
            
            tree = parser.parse(bytes(code, 'utf-8'))
            if not tree:
                logger.warning(f"Parser returned no tree for file: {file_path}")
                return {}
                
            result = self._normalize_ast(tree.root_node, code)
            logger.debug(f"Successfully parsed file: {file_path}")
            return result
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {str(e)}", exc_info=True)
            return {}

    def _normalize_ast(self, node: Any, code: str) -> Dict:
        """Convert AST node to normalized format, stripping unnecessary details."""
        if not node:
            return {}
            
        result = {
            'type': node.type,
            'children': []
        }
        
        # Handle different node types
        if node.type in ('function_declaration', 'method_definition'):
            # Normalize function/method declarations
            result['name'] = self._get_node_name(node)
            result['parameters'] = self._normalize_parameters(node)
            result['body'] = self._normalize_body(node, code)
            
        elif node.type in ('class_declaration', 'class_expression'):
            # Normalize class declarations
            result['name'] = self._get_node_name(node)
            result['methods'] = [
                self._normalize_ast(child, code)
                for child in node.children
                if child.type == 'method_definition'
            ]
            
        elif node.type in ('import_declaration', 'export_declaration'):
            # Normalize imports/exports
            result['source'] = self._get_import_source(node)
            result['specifiers'] = self._normalize_import_specifiers(node)
            
        elif node.type in ('for_statement', 'while_statement', 'if_statement'):
            # Normalize control flow structures
            result['condition'] = self._normalize_condition(node)
            result['body'] = self._normalize_body(node, code)
            
        else:
            # For other nodes, just include their children
            result['children'] = [
                self._normalize_ast(child, code)
                for child in node.children
            ]
            
        return result

    def _get_node_name(self, node: Any) -> str:
        """Extract normalized name from a node."""
        name_node = node.child_by_field_name('name')
        if name_node:
            return name_node.text.decode('utf-8')
        return ''

    def _normalize_parameters(self, node: Any) -> List[str]:
        """Normalize function parameters to generic names."""
        params = []
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for i, param in enumerate(params_node.children):
                if param.type == 'identifier':
                    params.append(f'param{i}')
        return params

    def _normalize_body(self, node: Any, code: str) -> Dict:
        """Normalize function/control flow body."""
        body_node = node.child_by_field_name('body')
        if body_node:
            return self._normalize_ast(body_node, code)
        return {}

    def _get_import_source(self, node: Any) -> str:
        """Extract import/export source."""
        source_node = node.child_by_field_name('source')
        if source_node:
            return source_node.text.decode('utf-8').strip('"\'')
        return ''

    def _normalize_import_specifiers(self, node: Any) -> List[Dict]:
        """Normalize import/export specifiers."""
        specifiers = []
        for child in node.children:
            if child.type in ('import_specifier', 'export_specifier'):
                spec = {
                    'type': child.type,
                    'name': self._get_node_name(child)
                }
                specifiers.append(spec)
        return specifiers

    def _normalize_condition(self, node: Any) -> Dict:
        """Normalize control flow conditions."""
        condition_node = node.child_by_field_name('condition')
        if condition_node:
            return self._normalize_ast(condition_node, '')
        return {}

    def compare_files(self, file1: str, file2: str) -> Dict:
        """Compare two JS/TS files and return similarity analysis, including function match counts."""
        tree1 = self.parse_file(file1)
        tree2 = self.parse_file(file2)
        
        # Calculate various similarity metrics
        function_similarity = self._compare_functions(tree1, tree2)
        import_similarity = self._compare_imports(tree1, tree2)
        class_similarity = self._compare_classes(tree1, tree2)
        control_flow_similarity = self._compare_control_flow(tree1, tree2)

        # Function-level match counts
        functions1 = self._extract_functions(tree1)
        functions2 = self._extract_functions(tree2)
        total_functions = max(len(functions1), len(functions2))
        matching_functions = 0
        different_functions = 0
        missing_functions = 0
        extra_functions = 0
        # For each function in file1, find best match in file2
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
        # Any functions in file2 not matched
        extra_functions = len(functions2) - len(matched2)
        # Calculate overall similarity score
        overall_similarity = (
            function_similarity * 0.4 +
            import_similarity * 0.2 +
            class_similarity * 0.2 +
            control_flow_similarity * 0.2
        )
        return {
            'similarity': round(overall_similarity, 2),
            'details': {
                'function_similarity': round(function_similarity, 2),
                'import_similarity': round(import_similarity, 2),
                'class_similarity': round(class_similarity, 2),
                'control_flow_similarity': round(control_flow_similarity, 2),
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

    def _compare_function_bodies(self, func1: Dict, func2: Dict) -> float:
        """Compare function bodies using tree similarity."""
        body1 = func1.get('body', {})
        body2 = func2.get('body', {})
        
        # Convert bodies to string representation for comparison
        str1 = str(body1)
        str2 = str(body2)
        
        return difflib.SequenceMatcher(None, str1, str2).ratio()

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