# Changelog

All notable changes to this project will be documented in this file.

---

## 🚀 v1.1.0 (Current)

### 🔧 General
- Major robustness improvements across all similarity checkers.
- Improved JSON report structure and UI transparency.
- Exclusion of boilerplate files (e.g., `next-env.d.ts`) from scoring.
- Added `ROADMAP.md` and `CHANGELOG.md` for better project transparency.
- Full update of documentation and `README.md` to reflect new logic.
- **Switched to tree-sitter installation by wheel for easy cross-platform installation.**

### 🧠 JS / TS
- Deep AST-based comparison with identifier and literal normalization.
- Call graph analysis with Jaccard similarity.
- Tree-structured function body similarity scoring.
- Penalization logic for unmatched files and individual functions.
- Granular metric breakdown:
  - Function bodies
  - Imports/exports
  - Class declarations
  - Control flow structures
  - Call graphs

### ⚛️ JSX / TSX
- Deep AST structure comparison for component trees.
- Identifier/literal normalization.
- Call graph and component body similarity analysis.
- Penalization for unmatched components/files.

### 🧾 HTML
- Improved DOM/AST-based structure comparison.
- Penalization for unmatched files and major DOM differences.

### 🎨 CSS
- Selector/property comparison with normalization of values (e.g., `10px` vs `10.0px`, `#fff` vs `#ffffff`).
- Penalization logic for unmatched selectors and files.

### 🌈 Tailwind CSS
- Jaccard and frequency-weighted similarity for extracted utility classes.
- Penalization for unmatched utility class sets and missing Tailwind usage.

### ⚙️ Tailwind Config
- Static key/value-based config comparison.
- Shared/unique value detection.
- Deep object diffing preparation for future enhancements.

---

## 🎉 v1.0.0 (First Release)
**Released: 2025-06-10**

### 🛠️ Features
- Upload and extract two zipped frontend web project folders.
- Automatic file matching using:
  - Exact name and path
  - Fuzzy filename similarity
  - Structure/content-based heuristics
- Per-file-type analyzers:
  - HTML, CSS, JSX/TSX
  - Tailwind CSS class usage
  - Tailwind config matching
- Similarity scoring engine:
  - Robust, weighted similarity metrics
  - Penalization for unmatched or renamed files
- Reporting:
  - JSON output with matched/unmatched file map
  - UI view for report interpretation
- Tree-sitter grammar support:
  - Prebuilt cross-platform binaries (Windows, Linux, macOS)
- CI/CD automation for grammar and binary updates

---

## 📝 Notes
- Each release will focus on a clear set of improvements, with backward-compatible updates where possible.
- Bug fixes and edge-case improvements may result in minor version bumps (e.g., `1.1.1`, `1.1.2`).

