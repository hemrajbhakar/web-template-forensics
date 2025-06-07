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
from core.css_style_checker import CSSStyleChecker

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
        # Check for files
        has_html = 'original_html_file' in request.files and 'user_html_file' in request.files and \
                   request.files['original_html_file'].filename and request.files['user_html_file'].filename
        has_jsx = 'original_jsx_file' in request.files and 'user_jsx_file' in request.files and \
                  request.files['original_jsx_file'].filename and request.files['user_jsx_file'].filename
        has_css = 'original_css_file' in request.files and 'user_css_file' in request.files and \
                  request.files['original_css_file'].filename and request.files['user_css_file'].filename

        if not has_html and not has_jsx and not has_css:
            return jsonify({'error': 'At least one pair of HTML, JSX, or CSS files is required'}), 400

        # Prepare temp file paths
        original_html_path = user_html_path = None
        original_jsx_path = user_jsx_path = None
        css_result = None
        if has_html:
            original_html = request.files['original_html_file']
            user_html = request.files['user_html_file']
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False, dir=TEMP_DIR) as orig_html_temp:
                original_html.save(orig_html_temp)
                original_html_path = Path(orig_html_temp.name)
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False, dir=TEMP_DIR) as user_html_temp:
                user_html.save(user_html_temp)
                user_html_path = Path(user_html_temp.name)
        if has_jsx:
            original_jsx = request.files['original_jsx_file']
            user_jsx = request.files['user_jsx_file']
            with tempfile.NamedTemporaryFile(suffix='.jsx', delete=False, dir=TEMP_DIR) as orig_jsx_temp:
                original_jsx.save(orig_jsx_temp)
                original_jsx_path = Path(orig_jsx_temp.name)
            with tempfile.NamedTemporaryFile(suffix='.jsx', delete=False, dir=TEMP_DIR) as user_jsx_temp:
                user_jsx.save(user_jsx_temp)
                user_jsx_path = Path(user_jsx_temp.name)
        if has_css:
            original_css = request.files['original_css_file'].read().decode('utf-8')
            user_css = request.files['user_css_file'].read().decode('utf-8')
            css_checker = CSSStyleChecker()
            css_result = css_checker.compare_css(original_css, user_css)

        # Always generate a unified report
        report_path = TEMP_DIR / 'report.json'
        report_data = {}
        # HTML/JSX analysis if present
        if has_html or has_jsx:
            if has_html and has_jsx:
                result = analyzer.analyze_templates(
                    original_html_path=original_html_path,
                    original_jsx_path=original_jsx_path,
                    user_html_path=user_html_path,
                    user_jsx_path=user_jsx_path
                )
            elif has_html:
                result = analyzer.analyze_html_only(
                    original_html_path=original_html_path,
                    user_html_path=user_html_path
                )
            elif has_jsx:
                result = analyzer.analyze_templates(
                    original_html_path=None,
                    original_jsx_path=original_jsx_path,
                    user_html_path=None,
                    user_jsx_path=user_jsx_path
                )
            analyzer.export_results(report_path)
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
        else:
            # Fill with not performed for html/jsx
            report_data = {
                'overall_similarity': 0.0,
                'prediction': '',
                'html_comparison': {
                    'similarity_score': 0.0,
                    'matching_elements': 0,
                    'different_elements': 0,
                    'missing_elements': 0,
                    'extra_elements': 0,
                    'summary': 'HTML comparison not performed.'
                },
                'jsx_comparison': {
                    'similarity_score': 0.0,
                    'matching_elements': 0,
                    'different_elements': 0,
                    'missing_elements': 0,
                    'extra_elements': 0,
                    'summary': 'JSX comparison not performed.'
                }
            }
        # Always add CSS result
        if css_result:
            report_data['css_comparison'] = css_result
        else:
            report_data['css_comparison'] = {
                'css_similarity': 0.0,
                'matching_selectors': 0,
                'different_selectors': 0,
                'missing_selectors': 0,
                'extra_selectors': 0,
                'media_queries': {},
                'summary': 'CSS comparison not performed.'
            }
        # Calculate overall_similarity as the average of all performed similarities
        sim_scores = []
        if report_data.get('html_comparison', {}).get('similarity_score', 0.0) > 0:
            sim_scores.append(report_data['html_comparison']['similarity_score'])
        if report_data.get('jsx_comparison', {}).get('similarity_score', 0.0) > 0:
            sim_scores.append(report_data['jsx_comparison']['similarity_score'])
        if report_data.get('css_comparison', {}).get('css_similarity', 0.0) > 0:
            sim_scores.append(report_data['css_comparison']['css_similarity'])
        if sim_scores:
            report_data['overall_similarity'] = sum(sim_scores) / len(sim_scores)
        else:
            report_data['overall_similarity'] = 0.0
        # Set prediction based on overall_similarity
        overall = report_data['overall_similarity']
        if overall >= 0.75:
            report_data['prediction'] = "High similarity — likely copied or derived"
        elif overall >= 0.40:
            report_data['prediction'] = "Moderate similarity — possible reuse or inspiration"
        else:
            report_data['prediction'] = "Low similarity — likely independent"
        # Save unified report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
        # Prepare frontend response
        return jsonify({
            'success': True,
            'similarity_scores': {
                'overall': report_data.get('overall_similarity', 0.0),
                'html': report_data.get('html_comparison', {}).get('similarity_score', 0.0),
                'jsx': report_data.get('jsx_comparison', {}).get('similarity_score', 0.0),
                'css': report_data.get('css_comparison', {}).get('css_similarity', 0.0)
            },
            'summary': {
                'html': {
                    'total_elements': sum([
                        report_data.get('html_comparison', {}).get('matching_elements', 0),
                        report_data.get('html_comparison', {}).get('different_elements', 0),
                        report_data.get('html_comparison', {}).get('missing_elements', 0),
                        report_data.get('html_comparison', {}).get('extra_elements', 0)
                    ]),
                    'matching_elements': report_data.get('html_comparison', {}).get('matching_elements', 0),
                    'different_elements': report_data.get('html_comparison', {}).get('different_elements', 0),
                    'missing_elements': report_data.get('html_comparison', {}).get('missing_elements', 0),
                    'extra_elements': report_data.get('html_comparison', {}).get('extra_elements', 0)
                },
                'jsx': {
                    'total_elements': sum([
                        report_data.get('jsx_comparison', {}).get('matching_elements', 0),
                        report_data.get('jsx_comparison', {}).get('different_elements', 0),
                        report_data.get('jsx_comparison', {}).get('missing_elements', 0),
                        report_data.get('jsx_comparison', {}).get('extra_elements', 0)
                    ]),
                    'matching_elements': report_data.get('jsx_comparison', {}).get('matching_elements', 0),
                    'different_elements': report_data.get('jsx_comparison', {}).get('different_elements', 0),
                    'missing_elements': report_data.get('jsx_comparison', {}).get('missing_elements', 0),
                    'extra_elements': report_data.get('jsx_comparison', {}).get('extra_elements', 0)
                },
                'css': {
                    'total_selectors': sum([
                        report_data.get('css_comparison', {}).get('matching_selectors', 0),
                        report_data.get('css_comparison', {}).get('different_selectors', 0),
                        report_data.get('css_comparison', {}).get('missing_selectors', 0),
                        report_data.get('css_comparison', {}).get('extra_selectors', 0)
                    ]),
                    'matching_selectors': report_data.get('css_comparison', {}).get('matching_selectors', 0),
                    'different_selectors': report_data.get('css_comparison', {}).get('different_selectors', 0),
                    'missing_selectors': report_data.get('css_comparison', {}).get('missing_selectors', 0),
                    'extra_selectors': report_data.get('css_comparison', {}).get('extra_selectors', 0)
                }
            },
            'prediction': report_data.get('prediction', ''),
            'css_result': report_data.get('css_comparison', {}),
            'report_url': '/download/report'
        })
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