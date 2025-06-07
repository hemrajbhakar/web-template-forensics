"""
Web Interface for Template Similarity Analysis
"""

import os
import sys
import tempfile
from pathlib import Path
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, request, jsonify, send_file
from core.forensic_analyzer import ForensicAnalyzer

app = Flask(__name__)
analyzer = ForensicAnalyzer()

# Use system temp directory instead of local uploads
TEMP_DIR = Path(tempfile.gettempdir()) / 'template_analyzer'
TEMP_DIR.mkdir(exist_ok=True)

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Handle file upload and analysis."""
    try:
        # Check for original HTML file
        if 'original_html_file' not in request.files:
            return jsonify({'error': 'Original HTML template is required'}), 400
        
        original_html = request.files['original_html_file']
        if not original_html.filename:
            return jsonify({'error': 'Original HTML template is required'}), 400
            
        # Check for user HTML file
        if 'user_html_file' not in request.files:
            return jsonify({'error': 'User HTML template is required'}), 400
            
        user_html = request.files['user_html_file']
        if not user_html.filename:
            return jsonify({'error': 'User HTML template is required'}), 400
        
        # Create temporary files with proper suffixes
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False, dir=TEMP_DIR) as orig_html_temp:
            original_html.save(orig_html_temp)
            original_html_path = Path(orig_html_temp.name)
            
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False, dir=TEMP_DIR) as user_html_temp:
            user_html.save(user_html_temp)
            user_html_path = Path(user_html_temp.name)
        
        # Check for optional JSX files
        has_jsx = False
        original_jsx_path = None
        user_jsx_path = None
        
        if 'original_jsx_file' in request.files and 'user_jsx_file' in request.files:
            original_jsx = request.files['original_jsx_file']
            user_jsx = request.files['user_jsx_file']
            
            if original_jsx.filename and user_jsx.filename:
                has_jsx = True
                with tempfile.NamedTemporaryFile(suffix='.jsx', delete=False, dir=TEMP_DIR) as orig_jsx_temp:
                    original_jsx.save(orig_jsx_temp)
                    original_jsx_path = Path(orig_jsx_temp.name)
                    
                with tempfile.NamedTemporaryFile(suffix='.jsx', delete=False, dir=TEMP_DIR) as user_jsx_temp:
                    user_jsx.save(user_jsx_temp)
                    user_jsx_path = Path(user_jsx_temp.name)
        
        try:
            # Analyze templates
            if has_jsx:
                result = analyzer.analyze_templates(
                    original_html_path=original_html_path,
                    original_jsx_path=original_jsx_path,
                    user_html_path=user_html_path,
                    user_jsx_path=user_jsx_path
                )
            else:
                result = analyzer.analyze_html_only(
                    original_html_path=original_html_path,
                    user_html_path=user_html_path
                )
            
            # Generate report
            report_path = TEMP_DIR / 'report.json'
            analyzer.export_results(report_path)
            
            # Get summary and scores
            summary = analyzer.get_structure_summary()
            similarity_scores = analyzer.get_similarity_scores()
            # Read prediction from report
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            prediction = report_data.get('prediction', '')
            
            return jsonify({
                'success': True,
                'similarity_scores': similarity_scores,
                'summary': summary,
                'prediction': prediction,
                'report_url': '/download/report'
            })
            
        finally:
            # Cleanup temporary files
            original_html_path.unlink(missing_ok=True)
            user_html_path.unlink(missing_ok=True)
            if has_jsx:
                original_jsx_path.unlink(missing_ok=True)
                user_jsx_path.unlink(missing_ok=True)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/report')
def download_report():
    """Download the analysis report."""
    report_path = TEMP_DIR / 'report.json'
    if report_path.exists():
        return send_file(
            report_path,
            mimetype='application/json',
            as_attachment=True,
            download_name='template_analysis_report.json'
        )
    return jsonify({'error': 'No report available'}), 404

if __name__ == '__main__':
    app.run(debug=True) 