"""
Tailwind Analyzer Module
Analyzes and compares Tailwind CSS configurations and usage.
"""

import json
import subprocess
from pathlib import Path

class TailwindAnalyzer:
    def __init__(self):
        self.config = None
        self.classes = set()
    
    def parse_config(self, config_path):
        """Parse tailwind.config.js using Node."""
        pass
    
    def extract_classes(self, content):
        """Extract and categorize Tailwind classes."""
        pass
    
    def compare_configs(self, original_config, user_config):
        """Compare two Tailwind configurations."""
        pass 