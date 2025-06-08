"""
Tailwind Analyzer Module
Analyzes and compares Tailwind CSS configurations and usage.
"""

import re
import json
import subprocess
from pathlib import Path
from typing import Set, Dict, Any
from bs4 import BeautifulSoup

class TailwindAnalyzer:
    def __init__(self):
        pass

    def extract_classes_html(self, content: str) -> set:
        """Extract Tailwind utility classes from all elements in HTML using BeautifulSoup."""
        soup = BeautifulSoup(content, 'html.parser')
        classes = set()
        for tag in soup.find_all(True):
            class_attr = tag.get('class')
            if class_attr:
                classes.update(class_attr)
        return classes

    def extract_classes_jsx(self, content: str) -> set:
        """Extract Tailwind utility classes from JSX/TSX using regex (fallback)."""
        class_regex = re.compile(r'(?:class|className)\s*=\s*["\"]([^"\"]+)["\"]')
        classes = set()
        for match in class_regex.findall(content):
            for cls in match.split():
                if cls:
                    classes.add(cls.strip())
        return classes

    def extract_classes(self, content: str, filetype: str) -> set:
        """Unified extraction function for HTML and JSX/TSX."""
        if filetype == 'html':
            return self.extract_classes_html(content)
        elif filetype in ('jsx', 'tsx'):
            return self.extract_classes_jsx(content)
        else:
            return set()

    def jaccard_similarity(self, set1: set, set2: set) -> float:
        if not set1 and not set2:
            return 1.0
        intersection = set1 & set2
        union = set1 | set2
        similarity = len(intersection) / len(union) if union else 0.0
        return similarity

    def compare_classes(self, original_content: str, user_content: str, filetype: str) -> dict:
        """Compare Tailwind classes in two markup files of the same type."""
        orig_classes = self.extract_classes(original_content, filetype)
        user_classes = self.extract_classes(user_content, filetype)
        print("EXTRACTED ORIG CLASSES:", orig_classes)
        print("EXTRACTED USER CLASSES:", user_classes)
        similarity = self.jaccard_similarity(orig_classes, user_classes)
        result = {
            'original_classes': list(orig_classes),
            'user_classes': list(user_classes),
            'shared_classes': list(orig_classes & user_classes),
            'only_in_original': list(orig_classes - user_classes),
            'only_in_user': list(user_classes - orig_classes),
            'jaccard_similarity': similarity
        }
        return result

    def parse_config(self, config_path: str) -> Dict[str, Any]:
        """Parse tailwind.config.js using Node.js and return as dict."""
        node_script = f"""
        const config = require('{config_path.replace('\\', '\\\\')}');
        console.log(JSON.stringify(config));
        """
        try:
            result = subprocess.run(['node', '-e', node_script], capture_output=True, text=True, check=True)
            config_json = result.stdout.strip()
            config = json.loads(config_json)
            print(f"[DEBUG] Parsed config from {config_path}: {config}")
            return config
        except Exception as e:
            print(f"[ERROR] Failed to parse config {config_path}: {e}")
            return {'error': str(e)}

    def extract_theme_extensions(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract theme extensions (colors, spacing, fontSize, etc.) from theme.extend."""
        theme = config.get('theme', {}) if isinstance(config, dict) else {}
        extend = theme.get('extend', {}) if isinstance(theme, dict) else {}
        extensions = {}
        for key in ['colors', 'spacing', 'fontSize', 'borderRadius', 'boxShadow', 'fontFamily', 'screens']:
            if key in extend:
                extensions[key] = extend[key]
        print(f"[DEBUG] Extracted theme extensions: {extensions}")
        return extensions

    def compare_configs(self, original_path: str, user_path: str) -> Dict[str, Any]:
        """Compare two Tailwind config files with detailed per-extension diff."""
        orig_cfg = self.parse_config(original_path)
        user_cfg = self.parse_config(user_path)
        orig_ext = self.extract_theme_extensions(orig_cfg)
        user_ext = self.extract_theme_extensions(user_cfg)
        orig_keys = set(orig_ext.keys())
        user_keys = set(user_ext.keys())
        key_intersection = orig_keys & user_keys
        key_union = orig_keys | user_keys
        key_similarity = len(key_intersection) / len(key_union) if key_union else 1.0
        # Detailed per-extension diff and subkey similarity
        shared_config_values = {}
        per_extension_similarity = {}
        subkey_similarities = []
        for ext_key in key_intersection:
            orig_val = orig_ext.get(ext_key, {})
            user_val = user_ext.get(ext_key, {})
            if isinstance(orig_val, dict) and isinstance(user_val, dict):
                orig_subkeys = set(orig_val.keys())
                user_subkeys = set(user_val.keys())
                shared_subkeys = orig_subkeys & user_subkeys
                only_in_original = {k: orig_val[k] for k in orig_subkeys - user_subkeys}
                only_in_user = {k: user_val[k] for k in user_subkeys - orig_subkeys}
                shared_config_values[ext_key] = {
                    'shared_keys': list(shared_subkeys),
                    'only_in_original': only_in_original,  # subkeys only in original config
                    'only_in_user': only_in_user           # subkeys only in user/modified config
                }
                # Jaccard similarity for subkeys
                subkey_union = orig_subkeys | user_subkeys
                subkey_intersection = shared_subkeys
                subkey_jaccard = len(subkey_intersection) / len(subkey_union) if subkey_union else 1.0
                per_extension_similarity[ext_key] = subkey_jaccard
                subkey_similarities.append(subkey_jaccard)
            else:
                # If not dict, just compare values
                shared_config_values[ext_key] = {
                    'original_value': orig_val,
                    'user_value': user_val,
                    'equal': orig_val == user_val
                }
                per_extension_similarity[ext_key] = 1.0 if orig_val == user_val else 0.0
                subkey_similarities.append(per_extension_similarity[ext_key])
        # Improved config similarity: average of top-level and all subkey Jaccards
        all_similarities = [key_similarity] + subkey_similarities if subkey_similarities else [key_similarity]
        improved_config_similarity = sum(all_similarities) / len(all_similarities) if all_similarities else 1.0
        # Output structure:
        # - shared_config_keys: top-level extension keys present in both
        # - only_in_original_config: top-level keys only in original
        # - only_in_user_config: top-level keys only in user
        # - shared_config_values: per-extension diffs (subkeys)
        # - per_extension_similarity: Jaccard for each shared extension
        result = {
            'original_config': orig_ext,
            'user_config': user_ext,
            'shared_config_keys': list(key_intersection),
            'only_in_original_config': list(orig_keys - user_keys),
            'only_in_user_config': list(user_keys - orig_keys),
            'key_jaccard_similarity': key_similarity,
            'shared_config_values': shared_config_values,
            'per_extension_similarity': per_extension_similarity,
            'improved_config_similarity': improved_config_similarity
        }
        print(f"[DEBUG] Tailwind config comparison result: {result}")
        return result 