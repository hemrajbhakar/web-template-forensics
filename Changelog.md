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

### 📦 JSON Comparison
- Added comparison for `package.json` and `tsconfig.json` files.
- Boilerplate-aware logic: common dependencies (`react`, `react-dom`, `next`) and scripts (`dev`, `build`, `start`, `lint`) are excluded from key similarity checks.
- Stricter meta field scoring: exact, normalized match for `name`, `version`, `description`, `author`; Jaccard for `keywords`.
- **Config file weighting:** `package.json` is counted as 2 virtual files and `tsconfig.json` as 1 virtual file in the overall file-count-based average, but only if present. This ensures config files have a fair, proportional impact on the overall similarity score.
- Weight reallocation: if a section is missing in both files, its weight is reallocated to dependencies for a more meaningful score.

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

