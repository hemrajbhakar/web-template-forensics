"""
File Utilities Module
Common file operations and path handling functions.
"""

import os
from pathlib import Path
from typing import Dict, List, Set

# File extension categories
EXTENSION_GROUPS = {
    'html': {'.html', '.htm'},
    'js': {'.js', '.jsx', '.ts', '.tsx'},
    'css': {'.css', '.scss', '.sass'},
    'config': {'.config.js', '.json'}
}

def normalize_path(path: str | Path) -> Path:
    """Convert string path to normalized Path object."""
    return Path(path).resolve()

def is_hidden(path: Path) -> bool:
    """Check if a file or directory is hidden."""
    # Check for hidden files/directories in Unix-like systems
    if path.name.startswith('.'):
        return True
    
    # Check for hidden files/directories in Windows
    try:
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        return attrs & 2 != 0
    except (AttributeError, ImportError):
        return False

def get_all_files_by_extension(path: str | Path, extensions: List[str]) -> List[Path]:
    """
    Recursively collect all files with specified extensions.
    
    Args:
        path: Base directory path
        extensions: List of file extensions to collect (e.g., ['.html', '.js'])
    
    Returns:
        List of Path objects for matching files
    """
    base_path = normalize_path(path)
    matching_files = []
    
    # Convert extensions to lowercase for case-insensitive matching
    extensions = [ext.lower() for ext in extensions]
    
    for root, dirs, files in os.walk(base_path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not is_hidden(Path(root) / d)]
        
        for file in files:
            file_path = Path(root) / file
            
            # Skip hidden files
            if is_hidden(file_path):
                continue
            
            # Check if file has any of the target extensions
            if any(file.lower().endswith(ext) for ext in extensions):
                matching_files.append(file_path)
    
    return matching_files

def collect_files(base_path: str | Path) -> Dict[str, List[Path]]:
    """
    Collect and categorize files from a directory.
    
    Args:
        base_path: Directory to scan for files
    
    Returns:
        Dictionary with categorized file paths:
        {
            'html': [list of html file paths],
            'js': [list of js/ts/jsx/tsx file paths],
            'css': [list of css file paths],
            'config': [config file paths]
        }
    """
    base_path = normalize_path(base_path)
    result = {category: [] for category in EXTENSION_GROUPS}
    
    # Walk through directory
    for root, dirs, files in os.walk(base_path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not is_hidden(Path(root) / d)]
        
        for file in files:
            file_path = Path(root) / file
            
            # Skip hidden files
            if is_hidden(file_path):
                continue
            
            # Categorize file based on extension
            for category, extensions in EXTENSION_GROUPS.items():
                # Special handling for .config.js files
                if category == 'config' and file == 'tailwind.config.js':
                    result[category].append(file_path)
                    break
                
                # Check regular extensions
                if any(file.lower().endswith(ext) for ext in extensions):
                    result[category].append(file_path)
                    break
    
    return result

def ensure_directory(directory: Path) -> None:
    """Ensure directory exists, create if necessary."""
    directory.mkdir(parents=True, exist_ok=True)

def read_file_content(file_path: Path) -> str:
    """
    Safely read file content with proper encoding.
    
    Args:
        file_path: Path to the file to read
    
    Returns:
        File contents as string
    
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Fallback to system default encoding if UTF-8 fails
        with open(file_path, 'r') as f:
            return f.read() 