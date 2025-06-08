# Forensic Template Comparison Tool

## Overview
This tool performs forensic comparison of two zipped web project folders, analyzing HTML, CSS, JSX/TSX, and Tailwind usage for structural and content similarity. It is designed for plagiarism detection, code review, and template analysis.

## Features
- **Upload two zip files** (original and modified project folders)
- **Automatic file matching** using:
  - Exact path-based match
  - Fuzzy filename similarity
  - Structure/content-based matching (AST for HTML/JSX, CSS property comparison)
  - Content similarity (for CSS)
  - Contextual (folder/neighbor) matching
- **Per-file-type comparison** (HTML, CSS, JSX/TSX)
- **Tailwind CSS analysis**:
  - Extracts and compares Tailwind utility classes from markup (HTML/JSX/TSX)
  - Computes Jaccard similarity between class sets
  - Parses and compares `tailwind.config.js` files (using Node.js)
  - Penalizes unmatched or highly divergent Tailwind usage/configs in the overall score
- **Extensible UI framework analyzer system** (easy to add analyzers for other frameworks)
- **Robust similarity scoring** with penalization for unmatched files
- **Detailed JSON and UI reporting**

## How It Works

### 1. Upload & Extraction
- User uploads two zip files: one for the original project, one for the modified project.
- Each zip is extracted to a temporary directory.

### 2. File Matching Logic
For each file type (HTML, CSS, JSX/TSX, Tailwind):
1. **Exact Path-Based Match:**
   - Files with the same relative path and filename are paired.
2. **Fuzzy Filename Match:**
   - Unmatched files are compared by filename similarity (using difflib). Pairs above a threshold are matched.
3. **Structure/AST-Based Match:**
   - For HTML/JSX: Compare DOM/AST structure (element count, depth, attributes, etc.).
   - For CSS: Compare selectors and property sets.
   - For Tailwind: Extract and compare utility classes from markup files.
4. **Content Similarity Match (CSS):**
   - For remaining unmatched CSS files, compare raw content similarity. Pairs above a threshold are matched.
5. **Contextual Match:**
   - Folder hierarchy and neighboring file matches are used to boost confidence for remaining unmatched files.

### 3. Per-File-Type Comparison
- **HTML/JSX:**
  - Uses AST/DOM structure comparison (element/tag/attribute analysis, fuzzy text, etc.).
- **CSS:**
  - For each matched selector, compares property-value pairs with normalization (e.g., `#fff` == `#ffffff`, `10px` == `10.0px`).
  - Selector similarity = number of matching properties / total unique properties.
  - Per-selector similarity is reported in the output.
- **Tailwind:**
  - Extracts all Tailwind utility classes from markup files.
  - Computes Jaccard similarity between class sets for each matched file pair.
  - Parses and compares `tailwind.config.js` files using Node.js, reporting key overlap and config differences.

### 4. Scoring and Penalization
- For each file type, the aggregate similarity score is:
  ```
  final_score = (sum of all similarity scores for matched pairs + 0.0 for each unmatched file) / total number of files involved
  ```
  - **Unmatched files** (present in only one folder) are penalized as 0.0 in the score.
  - **Total number of files** = number of original files + number of modified files - number of unique matched pairs.
- **CSS selector similarity:**
  - If selector similarity >= 0.9: counted as exact match.
  - If 0.3 <= similarity < 0.9: partial credit (actual similarity fraction).
  - If < 0.3: treated as different.
- **Tailwind class/config similarity:**
  - Jaccard similarity is used for class sets and config keys.
  - Highly divergent Tailwind usage/configs are penalized in the overall score.
- **Dynamic Weighted Overall Score:**
  - The overall similarity is a weighted average of the present categories (HTML, CSS, JSX, Tailwind):
    - Default weights: HTML 0.4, CSS 0.2, JSX 0.2, Tailwind 0.2
    - **Only categories with at least one file present in either folder are included.**
    - Weights are normalized so the sum is 1.0 for the present categories.
    - Example: If only HTML and CSS are present, weights become HTML 0.67, CSS 0.33.
- **Overall score** is the average of all per-type scores, weighted by the number of files and normalized weights.

### 5. Output & Reporting
- The tool returns a detailed JSON report including:
  - Per-type summary (HTML, CSS, JSX, Tailwind):
    - Number of files compared, matched, unmatched
    - List of matched pairs with similarity scores and match type
    - List of unmatched files (original and modified)
    - Aggregate similarity score (with penalization)
    - Per-selector similarity details for CSS
    - Per-file and config similarity details for Tailwind
  - Overall similarity score
  - Prediction verdicts (overall and per-type)
- The UI displays:
  - Overall and per-type similarity scores
  - Charts and breakdowns for each file type (including Tailwind)
  - Prediction verdicts
  - Lists of unmatched files
  - Tailwind class and config similarity breakdowns

## Example Scoring
If you have 2 matched CSS files (similarity 0.5 and 0.0) and 2 unmatched files, the final score is:
```
final_score = (0.5 + 0.0 + 0.0 + 0.0) / 4 = 0.125
```

## Usage
- Run the web app and upload two zip files via the UI.
- View the detailed similarity report and download the JSON report for further analysis.

## Requirements
- Python 3.8+
- Flask
- tinycss2
- BeautifulSoup4
- Node.js (for Tailwind config parsing)
- (See requirements.txt for full list)

## Notes
- Unmatched files are penalized in the final similarity score.
- All normalization and matching logic is robust to whitespace, formatting, and minor code changes.
- Tailwind analysis is extensible; more UI frameworks can be added easily.

---
For more details, see the code and comments in `core/file_matcher.py`, `core/css_style_checker.py`, `core/ui_framework_analyzer.py`, and `core/tailwind_analyzer.py`.

## Project Structure

```
jsx-forensic-tool/
├── core/
│   ├── __init__.py
│   ├── forensic_analyzer.py   # Main interface
│   ├── html_parser.py         # HTML parsing logic
│   ├── structure_comparator.py # Comparison logic
│   ├── tailwind_analyzer.py   # Tailwind utility class/config analysis
│   └── ui_framework_analyzer.py # UI framework analyzer manager (extensible)
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