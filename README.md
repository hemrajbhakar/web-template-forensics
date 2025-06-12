# Forensic Template Comparison Tool

![version](https://img.shields.io/badge/version-1.1.0-blue.svg)

<div align="center" style="margin: 1.5em 0;">
  <h2>🎯 <em>Similarity is shallow. Reuse runs deeper.</em></h2>
  <p style="font-size: 1.1em; color: #555; margin-top: 0.5em;">
    🧠 Not here to say they're just shaking hands — here to hint one might be standing on the other's shoulders.
  </p>
</div>

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
- **Boilerplate-Aware Comparison:**
  - Common dependencies (`react`, `react-dom`, `next`) and common scripts (`dev`, `build`, `start`, `lint`) are excluded from key similarity checks. Only custom/rare scripts and dependencies are considered for plagiarism signal.

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

### 3a. JavaScript/TypeScript (JS/TS) Similarity Model

The tool performs deep, structure-aware comparison of JavaScript and TypeScript files using the following approach:

- **Parsing:**
  - JS/TS files are parsed into abstract syntax trees (ASTs) using [tree-sitter](https://tree-sitter.github.io/tree-sitter/).
  - The ASTs are normalized to focus on code structure (functions, classes, imports, control flow) rather than raw text.
  - **All identifiers (variable, function, class names) and literals (strings, numbers, booleans) are normalized to generic tokens before comparison.**

- **What is Compared:**
  - **Functions:** Names, parameters, and **deep tree-based comparison of function bodies** (robust to reordering and minor edits).
  - **Imports/Exports:** Module sources and specifiers.
  - **Classes:** Class names and their methods.
  - **Control Flow:** Structures like `if`, `for`, `while` statements.
  - **Call Graph:** Function call relationships (who calls whom).

- **Similarity Calculation (Per-File):**
  - For each matched JS/TS file pair, the following weighted formula is used:
    ```
    overall_similarity = (
        0.35 * function_similarity +
        0.15 * import_similarity +
        0.15 * class_similarity +
        0.15 * control_flow_similarity +
        0.20 * call_graph_similarity
    )
    ```
  - **function_similarity** uses a deep, tree-based comparison of function bodies.
  - **call_graph_similarity** uses Jaccard similarity of function call edges.
  - Unmatched files are penalized as 0.0 in the aggregate.

- **Aggregate JS/TS Score:**
  - The aggregate JS/TS score is the average of all matched pairwise similarities, plus 0.0 for each unmatched file.

### 3b. JSX/TSX (React/Next.js Component) Similarity Model

- **Parsing:**
  - JSX/TSX files are parsed into ASTs using tree-sitter.
  - Identifiers and literals are normalized.

- **What is Compared:**
  - **Component/Function Structure:** AST/DOM structure (elements, attributes, etc.).
  - **Call Graph:** Component/function call relationships.
  - **Component/Function Body:** **Deep tree-based comparison** of all top-level function/component bodies.

- **Similarity Calculation (Per-File):**
  - For each matched JSX/TSX file pair, the following weighted formula is used:
    ```
    jsx_similarity_score = (
        0.6 * structure_similarity +
        0.2 * call_graph_similarity +
        0.2 * body_similarity
    )
    ```
  - **body_similarity** is the average best-match tree similarity of all top-level function/component bodies.
  - Unmatched files are penalized as 0.0 in the aggregate.

### 5. Scoring and Penalization (Updated)
- For each file type, the aggregate similarity score is:
  ```
  final_score = (sum of all similarity scores for matched pairs + 0.0 for each unmatched file + JSON config virtual file scores) / total number of files involved (including JSON virtual files if present)
  ```
  - **Unmatched files** are penalized as 0.0 in the score.
  - **Overall Similarity (File-Count-Based Average):**
    - The overall similarity is calculated as a file-count-based average of all per-file-type similarities (HTML, CSS, JSX/TSX, JS/TS, Tailwind, etc.), **plus JSON config files as virtual files if present**.
    - This means every matched or unmatched file, and each present config file, contributes equally to the final score, making the approach robust and fair regardless of project composition.
    - This method is preferred over a fixed weighted average, as it adapts to the actual file distribution in the compared projects.

#### 📦 JSON Config Virtual File Weights
| File            | Virtual File Count Weight | When Counted?                | Justification                                                |
| --------------- | ------------------------ | ---------------------------- | ------------------------------------------------------------ |
| `package.json`  | **2 files worth**        | Only if present in both zips | Contains dependencies, versions, scripts (multiple domains)  |
| `tsconfig.json` | **1 file worth**         | Only if present in both zips | Affects build, plugins, strictness — useful but lower impact |

- If a config file is missing in both projects, it is ignored and does not affect the overall score.
- If present, its similarity is counted as the specified number of virtual files in the denominator and numerator.

### Recent Improvements & Robustness
- **Identifier/Literal Normalization:** Robust to renaming and literal changes.
- **Call Graph Analysis:** Captures behavioral similarity, not just structure.
- **Deep Tree-Based Function/Component Body Comparison:** Robust to reordering, minor edits, and structural changes in logic-heavy files.
- **JSX/TSX Logic:** Now includes deep function/component body comparison, not just markup structure.
- **All weights and logic are documented above and kept up to date with the codebase.**
- **Boilerplate-Aware JSON Comparison:**
  - Common dependencies (`react`, `react-dom`, `next`) are excluded from dependency key similarity checks.
  - Common scripts (`dev`, `build`, `start`, `lint`) are excluded from script similarity checks.
  - Only custom/rare scripts and dependencies are considered for plagiarism signal.

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

## Files Always Excluded from Scoring

Certain files are excluded from similarity scoring because they are always (or almost always) identical across all React/Next.js projects and do not reflect meaningful code similarity. This helps ensure the scoring is fair and focused on real, project-specific code.

**Currently excluded files:**

1. `next-env.d.ts`  
   _Auto-generated by Next.js for TypeScript projects; always identical._

_This list may grow as the project evolves. If you notice other files that should be excluded, please open an issue or pull request!_

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

---

<div align="center" style="margin-top: 2em; font-style: italic; color: #888;">
  <strong>"Doesn't scream 'plagiarism' but whispers possibility."</strong>
</div>

---
