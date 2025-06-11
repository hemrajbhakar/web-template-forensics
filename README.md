# Forensic Template Comparison Tool

![version](https://img.shields.io/badge/version-1.0.0-blue.svg)

## Author
**Hemraj Bhakar**  \
_Full Stack Web Developer_

- [GitHub Profile](https://github.com/hemrajbhakar)
- [Portfolio Website](https://hemrajbhakar.site)

## Overview
This tool performs forensic comparison of two zipped web project folders, analyzing HTML, CSS, JSX/TSX, and Tailwind usage for structural and content similarity. It is designed for plagiarism detection, code review, and template analysis.

---

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

---

## How It Works

### 1. Upload & Extraction
- User uploads two zip files: one for the original project, one for the modified project.
- Each zip is extracted to a temporary directory.

### 2. File Matching Logic
For each file type (HTML, CSS, JSX/TSX, Tailwind):
1. **Exact Path-Based Match:** Files with the same relative path and filename are paired.
2. **Fuzzy Filename Match:** Unmatched files are compared by filename similarity.
3. **Structure/AST-Based Match:** For HTML/JSX, compare DOM/AST structure (element count, depth, attributes, etc.).
4. **Content Similarity Match (CSS):** For unmatched CSS files, compare raw content similarity.
5. **Contextual Match:** Folder hierarchy and neighboring file matches are used to boost confidence.

### 3. Per-File-Type Comparison
- **HTML/JSX/TSX:** Uses AST/DOM structure comparison (element/tag/attribute analysis, fuzzy text, etc.).
- **CSS:** Compares selectors and property-value pairs with normalization.
- **Tailwind:** Extracts all Tailwind utility classes from markup files and compares config files.

### 4. TSX/JSX Parsing Approach (NEW)
- Uses the [tree-sitter](https://tree-sitter.github.io/tree-sitter/) parser for robust, language-aware parsing of JSX/TSX files.
- **No Node.js required for parsing JSX/TSX!**
- **No manual .so/.dll/.dylib management for users:**  
  - The project uses a GitHub Actions workflow to build and commit prebuilt shared libraries (`my-languages.dll`, `.so`, `.dylib`) for all major platforms.
  - The Python code automatically loads the correct library for your OS:
    ```python
    import os, platform
    from tree_sitter import Language, Parser

    PLATFORM = platform.system().lower()
    if PLATFORM == 'windows':
        LIB_PATH = os.path.join(os.path.dirname(__file__), '..', 'prebuilt', 'windows-latest', 'my-languages.dll')
    elif PLATFORM == 'darwin':
        LIB_PATH = os.path.join(os.path.dirname(__file__), '..', 'prebuilt', 'macos-latest', 'my-languages.dylib')
    else:
        LIB_PATH = os.path.join(os.path.dirname(__file__), '..', 'prebuilt', 'ubuntu-latest', 'my-languages.so')

    LIB_PATH = os.path.abspath(LIB_PATH)
    TSX_LANGUAGE = Language(LIB_PATH, 'tsx')
    parser = Parser()
    parser.set_language(TSX_LANGUAGE)
    ```
  - This ensures **cross-platform compatibility** and up-to-date grammar support, as the grammars are rebuilt and committed automatically on every **tag push** (e.g., v1.0.0) or when manually triggered.

### 5. Scoring and Penalization
- For each file type, the aggregate similarity score is:
  ```
  final_score = (sum of all similarity scores for matched pairs + 0.0 for each unmatched file) / total number of files involved
  ```
  - **Unmatched files** are penalized as 0.0 in the score.
  - **Dynamic Weighted Overall Score:** The overall similarity is a weighted average of the present categories (HTML, CSS, JSX, Tailwind).

### 6. Output & Reporting
- The tool returns a detailed JSON report including per-type summaries, file matches, and overall similarity verdicts.
- The UI displays scores, charts, unmatched files, and Tailwind breakdowns.

---

## Usage

1. **Install dependencies:**
   ```sh
   python -m venv venv
   venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On macOS/Linux
   pip install -r requirements.txt
   python install.py  # Install tree-sitter wheel for your OS
   ```
2. **Run the web app:**
   ```sh
   python web/app.py
   ```
3. **Upload two zip files** via the UI and view/download the similarity report.

---

## Requirements
- Python 3.8–3.11
- Flask
- tinycss2
- BeautifulSoup4
- tree-sitter (installed via platform-specific wheel using install.py)
- Prebuilt shared libraries in `prebuilt/` (auto-managed by CI)
- Node.js (only for Tailwind config parsing)
- (See requirements.txt for full list)

---

## Project Structure

```
jsx-forensic-tool/
├── core/
│   ├── jsx_treesitter_parser.py   # TSX/JSX parsing logic (tree-sitter, OS-based)
│   └── ...
├── prebuilt/
│   ├── windows-latest/my-languages.dll
│   ├── macos-latest/my-languages.dylib
│   └── ubuntu-latest/my-languages.so
├── web/
│   └── app.py
├── requirements.txt
└── README.md
```

---

## CI/CD and Prebuilt Binaries
- **Continuous Integration (CI):**
  - On every **tag push** (e.g., v1.0.0) or when manually triggered, GitHub Actions automatically builds the latest tree-sitter grammars (including TSX/JSX) and commits the updated `.so`, `.dll`, and `.dylib` files to the `prebuilt/` directory.
  - This ensures all users always get the latest grammar support for each release, without manual compilation.
- **No need to build locally:**
  - Just pull the latest code and the correct binary for your OS will be used automatically.

---

## FAQ


**Q: Can I add more grammars?**
- Yes! Update the GitHub Actions workflow to include additional grammars when building the shared library.

**Q: What Python versions are supported?**
- Python 3.8–3.11 (due to binary compatibility of prebuilt grammars).

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

## License

MIT License

---

## Acknowledgments

- BeautifulSoup4 for HTML parsing
- Tree-sitter for JSX/TSX parsing
- Flask for web interface
- Chart.js for visualizations
- TailwindCSS for styling 