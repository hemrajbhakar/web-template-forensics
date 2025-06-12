# Roadmap

This roadmap outlines the completed, ongoing, and planned features for the Forensic Template Comparison Tool.

---

## ✅ Completed (as of v1.0.0)

- 🔍 Robust forensic comparison for zipped web project folders
- 🧠 Automatic file matching (exact path, fuzzy name, structure/content-based, context-aware)
- 📂 Per-file-type similarity analyzers:
  - HTML: AST/DOM structure comparison
  - CSS: Selector and normalized property comparison
  - JSX/TSX: AST, component/function body matching
  - JS/TS: AST-based comparison (function/class)
  - Tailwind CSS: Utility class extraction, Jaccard similarity
  - Tailwind config: Static config diffing
- 🧮 File-count-weighted scoring system (penalizes unmatched files fairly)
- 📊 Detailed JSON similarity reports with file-to-file mappings
- 🌐 Basic web UI to upload zips and view similarity report
- ⚙️ Prebuilt Tree-sitter binaries for Windows/macOS/Linux
- 🔄 CI/CD for automatic grammar updates and binary inclusion
- 📚 Documentation: README, CHANGELOG, ROADMAP

---

## ✅ Completed (as of v1.1.0)

- 🛠️ Switched to tree-sitter installation by wheel for easy cross-platform installation
- 🚫 Exclusion of boilerplate/static files (e.g. `next-env.d.ts`) from similarity scoring
- 🧠 Deep AST-based logic for JS/TS and JSX/TSX (identifier/literal normalization, call graph, tree-based function/component body comparison)
- 📈 Per-metric averages for JS/TS and JSX/TSX similarity (function, import, class, control flow, call graph)
- 🧾 Improved JSON report structure and UI transparency
- 🧮 Penalization logic for unmatched files/components/selectors/classes
- 📚 Full update of documentation and README to reflect new logic
- 📦 JSON comparison for `package.json` and `tsconfig.json` files
- 🚫 Boilerplate-aware logic for JSON: common dependencies (`react`, `react-dom`, `next`) and scripts (`dev`, `build`, `start`, `lint`) excluded from key similarity checks
- 🧾 Stricter meta field scoring: exact, normalized match for `name`, `version`, `description`, `author`; Jaccard for `keywords`
- 🔢 Config file weighting: `package.json` is counted as 2 virtual files and `tsconfig.json` as 1 virtual file in the overall similarity score, but only if present, for fairer config impact
- 🔄 Weight reallocation: missing section weights reallocated to dependencies for more meaningful score

---

## 🔧 In Progress

- 🔁 Collecting user feedback for edge cases and robustness improvements
- 🧹 Internal codebase refactoring for better maintainability and extensibility

---

## 🧭 Planned / Next

- 🖼️ Visual/semantic HTML/CSS diffing (pixel-level diffing and rendering)
- 🧬 Analysis of inline style attributes (`style=""`) and dynamic CSS usage
- 🎯 Support for CSS variables/custom properties and preprocessors (e.g. SCSS)
- ⚛️ Prop types and context API analysis for React/Next.js components
- 🧠 Static analysis of hooks/state usage (useEffect, useState, etc.)
- 🕸️ Module-level dependency graph for JS/TS files (who imports/exports what)
- 🔗 Semantic grouping and weighting of Tailwind utility classes
- 🧩 Deep nested diffing of Tailwind config object structures
- 🖼️ Analysis of non-code assets: images, icons, SVGs, fonts
- 📦 Comparison of common config files (e.g. `package.json`, `tsconfig.json`)
- 📚 More real-world usage examples, demo datasets, and tutorials
- 🟩 **Vue/Angular template similarity check feature**

---

## 📌 Notes

- Roadmap evolves with project goals and user/community feedback.
- Contributions are welcome for both planned and ongoing features.

