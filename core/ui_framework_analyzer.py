"""
UI Framework Analyzer Manager
Allows registration and execution of multiple UI framework analyzers (e.g., Tailwind, Bootstrap).
"""

from typing import Dict, Any, List
from .tailwind_analyzer import TailwindAnalyzer

class UIFrameworkAnalyzer:
    def __init__(self):
        self.analyzers = {}
        self.register_analyzer('tailwind', TailwindAnalyzer())
        # In the future, register more analyzers here

    def register_analyzer(self, name: str, analyzer):
        self.analyzers[name] = analyzer

    def analyze_all(self, file_pairs: List[Dict[str, Any]], config_pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run all registered analyzers and aggregate their results.
        file_pairs: List of dicts with keys: 'type', 'original_content', 'user_content'
        config_pairs: List of dicts with keys: 'type', 'original_path', 'user_path'
        """
        results = {}
        for name, analyzer in self.analyzers.items():
            # Analyze classes in markup files
            class_results = []
            for pair in file_pairs:
                if pair['type'] == name:
                    filetype = pair.get('filetype', 'html')
                    class_results.append(analyzer.compare_classes(pair['original_content'], pair['user_content'], filetype))
            # Analyze config files
            config_results = []
            for pair in config_pairs:
                if pair['type'] == name:
                    config_results.append(analyzer.compare_configs(pair['original_path'], pair['user_path']))
            results[name] = {
                'class_results': class_results,
                'config_results': config_results
            }
        return results 