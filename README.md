# JSX Forensic Analysis Tool

A powerful tool for analyzing and comparing HTML and JSX/TSX templates to identify structural differences, attribute mismatches, and potential conversion issues.

## Features

- **Template Comparison**: Compare HTML templates with their JSX/TSX counterparts
- **Structural Analysis**: Identify matching, different, missing, and extra elements
- **Attribute Analysis**: Deep comparison of HTML and JSX attributes, including:
  - Class name normalization
  - Style attribute parsing
  - Event handler mapping
  - Custom attribute handling
- **Visual Reports**: Interactive web interface with:
  - Similarity scoring
  - Element distribution charts
  - Detailed comparison reports
  - Downloadable JSON reports

## Prerequisites

1. Python 3.8 or higher
2. Node.js 14.0 or higher
3. Tree-sitter CLI

## Installation

1. Install Node.js and tree-sitter CLI:
```bash
# Install Node.js from https://nodejs.org/

# Install tree-sitter CLI
npm install -g tree-sitter-cli

# Install tree-sitter JavaScript grammar
git clone https://github.com/tree-sitter/tree-sitter-javascript
cd tree-sitter-javascript
npm install
tree-sitter generate
```

2. Clone the repository:
```bash
git clone https://github.com/yourusername/jsx-forensic-tool.git
cd jsx-forensic-tool
```

3. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Web Interface

1. Start the web server:
```bash
python web/app.py
```

2. Open your browser and navigate to `http://localhost:5000`

3. Upload your HTML and JSX/TSX files

4. View the analysis results and download detailed reports

### Python API

```python
from core.forensic_analyzer import ForensicAnalyzer

# Initialize the analyzer
analyzer = ForensicAnalyzer()

# Analyze files
result = analyzer.analyze_files('template.html', 'component.jsx')

# Get similarity score
score = analyzer.get_similarity_score()

# Generate report
analyzer.generate_report('report.txt')

# Export detailed results
analyzer.export_results('analysis.json')
```

## Project Structure

```
jsx-forensic-tool/
├── core/
│   ├── __init__.py
│   ├── forensic_analyzer.py   # Main interface
│   ├── html_parser.py         # HTML parsing logic
│   └── structure_comparator.py # Comparison logic
├── web/
│   ├── app.py                 # Flask web application
│   └── templates/
│       └── index.html         # Web interface template
├── tests/
│   ├── fixtures/              # Test files
│   ├── test_analyzer.py
│   ├── test_html_parser.py
│   └── test_comparator.py
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- BeautifulSoup4 for HTML parsing
- Tree-sitter for JSX parsing
- Flask for web interface
- Chart.js for visualizations
- TailwindCSS for styling 