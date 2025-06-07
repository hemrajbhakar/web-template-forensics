"""
Report Builder Module
Generates detailed comparison reports using Jinja2 templates.
"""

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

class ReportBuilder:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader("templates"))
        self.template = None
        self.data = {}
    
    def collect_metrics(self, comparison_results):
        """Collect and organize comparison metrics."""
        pass
    
    def generate_html_report(self, output_path):
        """Generate HTML report with comparisons and recommendations."""
        pass
    
    def generate_json_report(self, output_path):
        """Generate JSON report with raw comparison data."""
        pass 