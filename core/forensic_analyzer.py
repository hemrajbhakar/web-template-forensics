"""
Main Forensic Analyzer Interface
Coordinates HTML, JSX, and JS/TS template comparisons.
"""

from typing import Dict, Optional, Union, Tuple
from pathlib import Path
import json
from .html_parser import HTMLParser
from .structure_comparator import StructureComparator, ComparisonResult
import subprocess
import tempfile
from core.jsx_treesitter_parser import parse_jsx_with_treesitter, tree_similarity
from core.js_logic_analyzer import JSLogicAnalyzer

class TemplateComparison:
    def __init__(self, 
                 html_similarity: float,
                 jsx_similarity: float,
                 js_similarity: float,
                 html_details: ComparisonResult,
                 jsx_details: ComparisonResult,
                 js_details: Dict,
                 jsx_present: bool = True,
                 js_present: bool = True):
        self.html_similarity = html_similarity
        self.jsx_similarity = jsx_similarity
        self.js_similarity = js_similarity
        self.html_details = html_details
        self.jsx_details = jsx_details
        self.js_details = js_details
        # Determine which scores to use for overall_similarity
        scores = []
        weights = []
        if html_similarity > 0:
            scores.append(html_similarity)
            weights.append(0.3)
        if jsx_similarity > 0:
            scores.append(jsx_similarity)
            weights.append(0.3)
        if js_similarity > 0:
            scores.append(js_similarity)
            weights.append(0.4)
            
        if scores:
            # Normalize weights
            total_weight = sum(weights)
            weights = [w/total_weight for w in weights]
            self.overall_similarity = sum(s * w for s, w in zip(scores, weights))
        else:
            self.overall_similarity = 0.0

class ForensicAnalyzer:
    def __init__(self):
        self.html_parser = HTMLParser()
        self.comparator = StructureComparator()
        self.js_analyzer = JSLogicAnalyzer()
        self.last_result: Optional[TemplateComparison] = None
        
    def analyze_templates(self,
                        original_html_path: Union[str, Path, None],
                        original_jsx_path: Union[str, Path, None],
                        original_js_path: Union[str, Path, None],
                        user_html_path: Union[str, Path, None],
                        user_jsx_path: Union[str, Path, None],
                        user_js_path: Union[str, Path, None]) -> TemplateComparison:
        """Analyze and compare original and user templates (HTML, JSX, and JS/TS)."""
        # Parse HTML templates if paths are provided
        if original_html_path is not None and user_html_path is not None:
            original_html_tree = self.html_parser.parse_file(original_html_path)
            user_html_tree = self.html_parser.parse_file(user_html_path)
            html_result = self.comparator.compare_structures(original_html_tree, user_html_tree)
        else:
            html_result = ComparisonResult()  # empty/default result
        # Parse JSX templates if paths are provided
        jsx_call_graph_similarity = 0.0
        jsx_body_similarity = 1.0
        if original_jsx_path is not None and user_jsx_path is not None:
            original_jsx = parse_jsx_with_treesitter(str(original_jsx_path))
            user_jsx = parse_jsx_with_treesitter(str(user_jsx_path))
            # Compare normalized ASTs for structure similarity
            jsx_struct_result = self.comparator.compare_structures(original_jsx['ast'], user_jsx['ast'])
            # Compare call graphs for call graph similarity
            jsx_call_graph_similarity = self._compare_call_graphs_jsx(user_jsx['call_graph'], original_jsx['call_graph'])
            # --- Deeper function/component body comparison ---
            def extract_functions(ast):
                results = []
                def traverse(node):
                    if node.get('type') in ('function_declaration', 'function_expression', 'arrow_function', 'method_definition'):
                        results.append(node)
                    for child in node.get('children', []):
                        traverse(child)
                traverse(ast)
                return results
            orig_funcs = extract_functions(original_jsx['ast'])
            user_funcs = extract_functions(user_jsx['ast'])
            # Pairwise best-match similarity (greedy)
            matched = 0
            used2 = set()
            for f1 in orig_funcs:
                best = 0.0
                best_j = -1
                for j, f2 in enumerate(user_funcs):
                    if j in used2:
                        continue
                    sim = tree_similarity(f1.get('body', {}), f2.get('body', {}))
                    if sim > best:
                        best = sim
                        best_j = j
                if best_j >= 0:
                    used2.add(best_j)
                matched += best
            total = max(len(orig_funcs), len(user_funcs))
            jsx_body_similarity = matched / total if total else 1.0
            # Combine structure, call graph, and body similarity (e.g., 60/20/20)
            jsx_similarity_score = jsx_struct_result.similarity_score * 0.6 + jsx_call_graph_similarity * 0.2 + jsx_body_similarity * 0.2
            # Store details for reporting
            jsx_result = jsx_struct_result
            jsx_result.call_graph_similarity = jsx_call_graph_similarity
            jsx_result.body_similarity = jsx_body_similarity
            jsx_result.similarity_score = jsx_similarity_score
        else:
            jsx_result = ComparisonResult()  # empty/default result
        # Parse JS/TS files if paths are provided
        if original_js_path is not None and user_js_path is not None:
            js_result = self.js_analyzer.compare_files(original_js_path, user_js_path)
        else:
            js_result = {'similarity': 0.0, 'details': {}}
        # Determine if JSX/JS trees have nodes
        jsx_present = (original_jsx_path is not None and user_jsx_path is not None)
        js_present = (original_js_path is not None and user_js_path is not None)
        # Create combined result
        self.last_result = TemplateComparison(
            html_similarity=html_result.similarity_score,
            jsx_similarity=jsx_result.similarity_score,
            js_similarity=js_result['similarity'],
            html_details=html_result,
            jsx_details=jsx_result,
            js_details=js_result,
            jsx_present=jsx_present,
            js_present=js_present
        )
        return self.last_result
    
    def _parse_jsx(self, content: str) -> Dict:
        """Parse JSX content using the Python tree-sitter parser (prebuilt binary)."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.jsx', delete=False, mode='w', encoding='utf-8') as jsx_file:
                jsx_file.write(content)
                jsx_file_path = jsx_file.name
            ast = parse_jsx_with_treesitter(jsx_file_path)
            return ast
        except Exception as e:
            print(f"Error running Python tree-sitter JSX parser: {e}")
            return {}
    
    def generate_report(self, output_path: Optional[Union[str, Path]] = None) -> str:
        """Generate a detailed analysis report."""
        if not self.last_result:
            return "No analysis has been performed yet."
            
        report = [
            "Template Comparison Report",
            "=========================\n",
            f"Overall Similarity Score: {self.last_result.overall_similarity:.2%}\n",
            "HTML Template Comparison:",
            f"- Similarity Score: {self.last_result.html_similarity:.2%}",
            "- Details:",
            self.comparator.generate_diff_report(self.last_result.html_details),
            "\nJSX Template Comparison:",
            f"- Similarity Score: {self.last_result.jsx_similarity:.2%}",
            "- Details:",
            self.comparator.generate_diff_report(self.last_result.jsx_details)
        ]
        
        report_text = "\n".join(report)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
        
        return report_text
    
    def _generate_summary(self, result):
        """Generate a human-readable summary string for a ComparisonResult."""
        match = len(result.matching_elements)
        diff = len(result.different_elements)
        miss = len(result.missing_elements)
        extra = len(result.extra_elements)
        summary_parts = []
        if match > 0 and diff == 0 and miss == 0 and extra == 0:
            summary_parts.append("All elements match structurally.")
        else:
            if diff > 0:
                summary_parts.append(f"{diff} elements differ (attributes or text)")
            if miss > 0:
                summary_parts.append(f"{miss} element(s) missing")
            if extra > 0:
                summary_parts.append(f"{extra} extra element(s)")
            if match > 0:
                summary_parts.append(f"{match} elements match structurally")
        return "; ".join(summary_parts) if summary_parts else "No elements compared."

    def _get_prediction(self, score):
        if score >= 0.75:
            return "High similarity — likely copied or derived"
        elif score >= 0.40:
            return "Moderate similarity — possible reuse or inspiration"
        else:
            return "Low similarity — likely independent"

    def export_results(self, output_path: Union[str, Path]) -> None:
        """Export analysis results to JSON."""
        if not self.last_result:
            raise ValueError("No analysis has been performed yet.")
        html = self.last_result.html_details
        jsx = self.last_result.jsx_details
        js = self.last_result.js_details
        html_summary = self._generate_summary(html)
        jsx_summary = self._generate_summary(jsx) if jsx is not None else "No JSX comparison performed."
        js_summary = "No JS/TS comparison performed."
        if js and isinstance(js, dict):
            js_summary = f"Function similarity: {js.get('details', {}).get('function_similarity', 0):.2%}, " \
                        f"Import similarity: {js.get('details', {}).get('import_similarity', 0):.2%}, " \
                        f"Class similarity: {js.get('details', {}).get('class_similarity', 0):.2%}, " \
                        f"Control flow similarity: {js.get('details', {}).get('control_flow_similarity', 0):.2%}, " \
                        f"Call graph similarity: {js.get('details', {}).get('call_graph_similarity', 0):.2%}"
        # Add call graph similarity to JSX report if present
        jsx_call_graph_similarity = getattr(jsx, 'call_graph_similarity', None)
        result_dict = {
            "overall_similarity": self.last_result.overall_similarity,
            "prediction": self._get_prediction(self.last_result.overall_similarity),
            "html_comparison": {
                "similarity_score": self.last_result.html_similarity,
                "matching_elements": len(html.matching_elements),
                "different_elements": len(html.different_elements),
                "missing_elements": len(html.missing_elements),
                "extra_elements": len(html.extra_elements),
                "summary": html_summary
            },
            "jsx_comparison": {
                "similarity_score": self.last_result.jsx_similarity if jsx is not None else 0.0,
                "matching_elements": len(jsx.matching_elements) if jsx is not None else 0,
                "different_elements": len(jsx.different_elements) if jsx is not None else 0,
                "missing_elements": len(jsx.missing_elements) if jsx is not None else 0,
                "extra_elements": len(jsx.extra_elements) if jsx is not None else 0,
                "call_graph_similarity": jsx_call_graph_similarity if jsx_call_graph_similarity is not None else 0.0,
                "body_similarity": getattr(jsx, 'body_similarity', 0.0) if jsx is not None else 0.0,
                "summary": jsx_summary
            },
            "js_comparison": {
                "similarity_score": self.last_result.js_similarity if js is not None else 0.0,
                "function_similarity": js.get('details', {}).get('function_similarity', 0) if js is not None else 0.0,
                "import_similarity": js.get('details', {}).get('import_similarity', 0) if js is not None else 0.0,
                "class_similarity": js.get('details', {}).get('class_similarity', 0) if js is not None else 0.0,
                "control_flow_similarity": js.get('details', {}).get('control_flow_similarity', 0) if js is not None else 0.0,
                "call_graph_similarity": js.get('details', {}).get('call_graph_similarity', 0) if js is not None else 0.0,
                "summary": js_summary
            }
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2)
            
    def analyze_html_only(self,
                      original_html_path: Union[str, Path],
                      user_html_path: Union[str, Path]) -> TemplateComparison:
        """Analyze and compare HTML templates only."""
        # Parse HTML templates
        original_html_tree = self.html_parser.parse_file(original_html_path)
        user_html_tree = self.html_parser.parse_file(user_html_path)
        
        # Compare HTML templates
        html_result = self.comparator.compare_structures(original_html_tree, user_html_tree)
        
        # Create result with HTML comparison only
        self.last_result = TemplateComparison(
            html_similarity=html_result.similarity_score,
            jsx_similarity=0.0,  # No JSX comparison
            js_similarity=0.0,  # No JS comparison
            html_details=html_result,
            jsx_details=None,  # No JSX details
            js_details={},  # No JS details
            jsx_present=False,  # JSX not present
            js_present=False  # JS not present
        )
        
        return self.last_result
        
    def get_similarity_scores(self) -> Dict[str, float]:
        """Get all similarity scores from the last analysis."""
        if not self.last_result:
            raise ValueError("No analysis has been performed yet.")
            
        scores = {
            'html': self.last_result.html_similarity,
            'overall': self.last_result.html_similarity  # For HTML-only, overall = HTML score
        }
        
        # Add JSX score only if JSX was compared
        if self.last_result.jsx_details is not None:
            scores['jsx'] = self.last_result.jsx_similarity
            scores['overall'] = self.last_result.overall_similarity
            
        # Add JS score only if JS was compared
        if self.last_result.js_details:
            scores['js'] = self.last_result.js_similarity
            scores['overall'] = self.last_result.overall_similarity
            
        return scores
        
    def get_structure_summary(self) -> Dict:
        """Get a summary of structural differences."""
        if not self.last_result:
            raise ValueError("No analysis has been performed yet.")
        
        html = self.last_result.html_details
        jsx = self.last_result.jsx_details
        
        summary = {
            "html": {
                "total_elements": (
                    len(html.matching_elements) +
                    len(html.different_elements) +
                    len(html.missing_elements) +
                    len(html.extra_elements)
                ),
                "matching_elements": len(html.matching_elements),
                "different_elements": len(html.different_elements),
                "missing_elements": len(html.missing_elements),
                "extra_elements": len(html.extra_elements)
            }
        }
        
        # Add JSX summary only if JSX was compared
        if jsx is not None:
            summary["jsx"] = {
                "total_elements": (
                    len(jsx.matching_elements) +
                    len(jsx.different_elements) +
                    len(jsx.missing_elements) +
                    len(jsx.extra_elements)
                ),
                "matching_elements": len(jsx.matching_elements),
                "different_elements": len(jsx.different_elements),
                "missing_elements": len(jsx.missing_elements),
                "extra_elements": len(jsx.extra_elements)
            }
        else:
            summary["jsx"] = {
                "total_elements": 0,
                "matching_elements": 0,
                "different_elements": 0,
                "missing_elements": 0,
                "extra_elements": 0
            }
        
        return summary 

    def _compare_call_graphs_jsx(self, cg1, cg2):
        # Compare two call graphs using Jaccard similarity of edges (copied from js_logic_analyzer)
        edges1 = set((caller, callee) for caller, callees in cg1.items() for callee in callees)
        edges2 = set((caller, callee) for caller, callees in cg2.items() for callee in callees)
        if not edges1 and not edges2:
            return 1.0
        if not edges1 or not edges2:
            return 0.0
        intersection = len(edges1 & edges2)
        union = len(edges1 | edges2)
        return intersection / union if union else 0.0 