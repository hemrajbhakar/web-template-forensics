"""
Setup script for installing and building tree-sitter parsers.
"""

import os
import subprocess
from pathlib import Path
from tree_sitter import Language

def clone_grammar(repo_url: str, target_dir: Path):
    """Clone a tree-sitter grammar repository."""
    if not target_dir.exists():
        subprocess.run(['git', 'clone', repo_url, str(target_dir)], check=True)
        # Some grammars need npm install to build
        if (target_dir / 'package.json').exists():
            subprocess.run(['npm', 'install'], cwd=target_dir, check=True)

def build_language_lib(build_dir: Path, grammar_paths: list):
    """Builds the shared library for Tree-sitter parsers."""
    lib_path = build_dir / 'my-languages.so'
    
    try:
        Language.build_library(
            str(lib_path),
            [str(path) for path in grammar_paths]
        )
        print(f"✅ Language library built at: {lib_path}")
    except Exception as e:
        print(f"❌ Failed to build language library: {e}")
        raise

def main():
    # Get the project root directory
    root_dir = Path(__file__).parent
    
    # Create build directory if it doesn't exist
    build_dir = root_dir / 'build'
    build_dir.mkdir(exist_ok=True)
    
    # Clone the required tree-sitter grammars
    grammars = {
        'tree-sitter-javascript': 'https://github.com/tree-sitter/tree-sitter-javascript.git',
        'tree-sitter-typescript': 'https://github.com/tree-sitter/tree-sitter-typescript.git'
    }
    
    print("🚀 Setting up tree-sitter parsers...")
    
    for grammar_dir, repo_url in grammars.items():
        target_dir = root_dir / grammar_dir
        print(f"📦 Cloning {grammar_dir}...")
        clone_grammar(repo_url, target_dir)
    
    # Build the language library
    print("🔨 Building language library...")
    grammar_paths = [
        root_dir / 'tree-sitter-javascript',
        root_dir / 'tree-sitter-typescript' / 'typescript'  # Note: TypeScript grammar is in a subdirectory
    ]
    build_language_lib(build_dir, grammar_paths)
    
    print("✨ Setup complete!")

if __name__ == "__main__":
    main() 