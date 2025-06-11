"""
Web Interface for Template Similarity Analysis
"""

import os
import sys
import tempfile
from pathlib import Path
import json
import glob
import tree_sitter
try:
    import importlib.metadata
    version = importlib.metadata.version("tree-sitter")
except ImportError:
    import pkg_resources
    version = pkg_resources.get_distribution("tree-sitter").version

print("Python version:", sys.version)

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, request, jsonify, send_file
from core.forensic_analyzer import ForensicAnalyzer
from core.css_style_checker import CSSStyleChecker
from core.file_matcher import unzip_to_tempdir, match_and_compare_all
from core.ui_framework_analyzer import UIFrameworkAnalyzer

app = Flask(__name__)
analyzer = ForensicAnalyzer()

# Use system temp directory instead of local uploads
TEMP_DIR = Path(tempfile.gettempdir()) / 'template_analyzer'
TEMP_DIR.mkdir(exist_ok=True)

def aggregate_html_summary(pairs):
    total = matching = different = missing = extra = 0
    for pair in pairs:
        summary = pair.get('details', {}).get('summary', {}).get('html', {})
        total += summary.get('total_elements', 0)
        matching += summary.get('matching_elements', 0)
        different += summary.get('different_elements', 0)
        missing += summary.get('missing_elements', 0)
        extra += summary.get('extra_elements', 0)
    return {
        'total_elements': total,
        'matching_elements': matching,
        'different_elements': different,
        'missing_elements': missing,
        'extra_elements': extra
    }

def aggregate_jsx_summary(pairs):
    total = matching = different = missing = extra = 0
    for pair in pairs:
        summary = pair.get('details', {}).get('summary', {}).get('jsx', {})
        total += summary.get('total_elements', 0)
        matching += summary.get('matching_elements', 0)
        different += summary.get('different_elements', 0)
        missing += summary.get('missing_elements', 0)
        extra += summary.get('extra_elements', 0)
    return {
        'total_elements': total,
        'matching_elements': matching,
        'different_elements': different,
        'missing_elements': missing,
        'extra_elements': extra
    }

def aggregate_css_summary(pairs):
    total = matching = different = missing = extra = 0
    for pair in pairs:
        details = pair.get('details', {})
        matching += details.get('matching_selectors', 0)
        different += details.get('different_selectors', 0)
        missing += details.get('missing_selectors', 0)
        extra += details.get('extra_selectors', 0)
    total = matching + different + missing + extra
    return {
        'total_selectors': total,
        'matching_selectors': matching,
        'different_selectors': different,
        'missing_selectors': missing,
        'extra_selectors': extra
    }

def aggregate_js_summary(pairs):
    total = matching = different = missing = extra = 0
    sum_func = sum_import = sum_class = sum_control = sum_callgraph = 0.0
    count = 0
    for pair in pairs:
        details = pair.get('details', {})
        total += details.get('total_functions', 0)
        matching += details.get('matching_functions', 0)
        different += details.get('different_functions', 0)
        missing += details.get('missing_functions', 0)
        extra += details.get('extra_functions', 0)
        if 'function_similarity' in details:
            sum_func += details.get('function_similarity', 0.0)
            sum_import += details.get('import_similarity', 0.0)
            sum_class += details.get('class_similarity', 0.0)
            sum_control += details.get('control_flow_similarity', 0.0)
            sum_callgraph += details.get('call_graph_similarity', 0.0)
            count += 1
    avg_func = sum_func / count if count else 0.0
    avg_import = sum_import / count if count else 0.0
    avg_class = sum_class / count if count else 0.0
    avg_control = sum_control / count if count else 0.0
    avg_callgraph = sum_callgraph / count if count else 0.0
    return {
        'total_functions': total,
        'matching_functions': matching,
        'different_functions': different,
        'missing_functions': missing,
        'extra_functions': extra,
        'function_similarity': avg_func,
        'import_similarity': avg_import,
        'class_similarity': avg_class,
        'control_flow_similarity': avg_control,
        'call_graph_similarity': avg_callgraph
    }

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

@app.route('/analyze_zip', methods=['POST'])
def analyze_zip():
    """Handle two zip file uploads, run full project comparison, and return JSON for UI."""
    try:
        if 'original_zip' not in request.files or 'modified_zip' not in request.files:
            return jsonify({'error': 'Both original and modified zip files are required.'}), 400
        orig_zip = request.files['original_zip']
        mod_zip = request.files['modified_zip']
        if not orig_zip.filename.endswith('.zip') or not mod_zip.filename.endswith('.zip'):
            return jsonify({'error': 'Only .zip files are accepted.'}), 400
        # Save and unzip
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False, dir=TEMP_DIR) as orig_zip_temp:
            orig_zip.save(orig_zip_temp)
            orig_zip_path = orig_zip_temp.name
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False, dir=TEMP_DIR) as mod_zip_temp:
            mod_zip.save(mod_zip_temp)
            mod_zip_path = mod_zip_temp.name
        orig_dir = unzip_to_tempdir(orig_zip_path)
        mod_dir = unzip_to_tempdir(mod_zip_path)
        # Find Tailwind config files in both directories
        orig_config_files = glob.glob(os.path.join(orig_dir, '**', 'tailwind.config.js'), recursive=True)
        mod_config_files = glob.glob(os.path.join(mod_dir, '**', 'tailwind.config.js'), recursive=True)
        config_pairs = []
        for orig_cfg in orig_config_files:
            for mod_cfg in mod_config_files:
                config_pairs.append({
                    'type': 'tailwind',
                    'original_path': orig_cfg,
                    'user_path': mod_cfg
                })
        # Run matcher
        results = match_and_compare_all(orig_dir, mod_dir)
        # Update summary['tailwind'] to use the robust structure
        tailwind = results.get('tailwind', {})
        results['summary'] = {
            'html': aggregate_html_summary(results.get('html', {}).get('matched_pairs', [])),
            'jsx': aggregate_jsx_summary(results.get('jsx', {}).get('matched_pairs', [])),
            'css': aggregate_css_summary(results.get('css', {}).get('matched_pairs', [])),
            'js': aggregate_js_summary(results.get('js', {}).get('matched_pairs', [])),
            'tailwind': tailwind  # Use the full robust tailwind result
        }
        # Add compatibility field for frontend
        html_score = results.get('html', {}).get('aggregate_score', 0.0)
        css_score = results.get('css', {}).get('aggregate_score', 0.0)
        jsx_score = results.get('jsx', {}).get('aggregate_score', 0.0)
        tailwind_score = tailwind.get('class_similarity', 0.0)
        # Remove base_weights and weighted average logic
        # Only use file-count-based overall_similarity (already computed in match_and_compare_all)
        results['similarity_scores'] = {
            'html': html_score,
            'jsx': jsx_score,
            'css': css_score,
            'js': results.get('js', {}).get('aggregate_score', 0.0),
            'tailwind': tailwind_score
        }
        # Ensure both similarity and similarity_scores['overall'] use the file-count-based value
        results['similarity_scores']['overall'] = results.get('overall_similarity', 0.0)
        # Optionally, save report for download
        report_path = TEMP_DIR / 'report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        results['report_url'] = '/download/report'
        # Use the backend's summary as-is, but future-proof: always include all keys
        summary = {k: v for k, v in results['summary'].items()}
        compact_results = {
            'similarity': results.get('overall_similarity', 0.0),
            'similarity_scores': results.get('similarity_scores', {}),
            'summary': summary,  # Use all keys present in backend summary
            'file_matches': {
                'html': results.get('html', {}).get('matched_pairs', []),
                'css': results.get('css', {}).get('matched_pairs', []),
                'jsx': results.get('jsx', {}).get('matched_pairs', []),
                'js': results.get('js', {}).get('matched_pairs', []),
                'tailwind': tailwind.get('per_file_results', []),
                'unmatched': {
                    'html': results.get('html', {}).get('unmatched_files', {}),
                    'css': results.get('css', {}).get('unmatched_files', {}),
                    'jsx': results.get('jsx', {}).get('unmatched_files', {}),
                    'js': results.get('js', {}).get('unmatched_files', {})
                }
            },
            'prediction': results.get('prediction', ''),
            'report_url': results.get('report_url', '')
        }
        return jsonify(compact_results)
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)