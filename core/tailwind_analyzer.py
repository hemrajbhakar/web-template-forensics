"""
Tailwind Analyzer Module
Analyzes and compares Tailwind CSS configurations and usage.
"""

import re
import json
import subprocess
from pathlib import Path
from typing import Set, Dict, Any, Tuple, List
from bs4 import BeautifulSoup
from collections import Counter, defaultdict

class TailwindAnalyzer:
    def __init__(self):
        pass

    def extract_classes_html(self, content: str) -> Tuple[Counter, Dict[str, List[str]]]:
        """Extract Tailwind classes and their locations from HTML using BeautifulSoup."""
        soup = BeautifulSoup(content, 'html.parser')
        class_counter = Counter()
        class_locations = defaultdict(list)
        for tag in soup.find_all(True):
            class_attr = tag.get('class')
            if class_attr:
                for cls in class_attr:
                    class_counter[cls] += 1
                    # Use tag name and a string of attributes as a simple location
                    location = f"<{tag.name} {' '.join([f'{k}={v}' for k,v in tag.attrs.items() if k != 'class'])}>"
                    class_locations[cls].append(location)
        return class_counter, dict(class_locations)

    def extract_classes_jsx(self, content: str) -> Tuple[Counter, Dict[str, List[str]]]:
        """Extract Tailwind classes and their locations from JSX/TSX using regex (fallback)."""
        class_regex = re.compile(r'(?:class|className)\s*=\s*["\"]([^"\"]+)["\"]')
        class_counter = Counter()
        class_locations = defaultdict(list)
        for match in class_regex.finditer(content):
            classes = match.group(1).split()
            # Try to get a bit of context: the line number
            line_no = content[:match.start()].count('\n') + 1
            for cls in classes:
                if cls:
                    class_counter[cls.strip()] += 1
                    class_locations[cls.strip()].append(f"line {line_no}")
        return class_counter, dict(class_locations)

    def extract_classes(self, content: str, filetype: str) -> Tuple[Counter, Dict[str, List[str]]]:
        """Unified extraction function for HTML and JSX/TSX."""
        if filetype == 'html':
            return self.extract_classes_html(content)
        elif filetype in ('jsx', 'tsx'):
            return self.extract_classes_jsx(content)
        else:
            return Counter(), {}

    def frequency_weighted_jaccard(self, c1: Counter, c2: Counter) -> float:
        """Compute frequency-weighted Jaccard similarity for two Counters."""
        intersection = sum((c1 & c2).values())
        union = sum((c1 | c2).values())
        return intersection / union if union else 1.0

    def set_jaccard_similarity(self, set1: set, set2: set) -> float:
        if not set1 and not set2:
            return 1.0
        intersection = set1 & set2
        union = set1 | set2
        similarity = len(intersection) / len(union) if union else 0.0
        return similarity

    def compare_classes(self, original_content: str, user_content: str, filetype: str) -> dict:
        """Compare Tailwind classes in two markup files of the same type, with frequency and location info."""
        orig_counter, orig_locations = self.extract_classes(original_content, filetype)
        user_counter, user_locations = self.extract_classes(user_content, filetype)
        shared_classes = set(orig_counter) & set(user_counter)
        only_in_original = set(orig_counter) - set(user_counter)
        only_in_user = set(user_counter) - set(orig_counter)
        freq_jaccard = self.frequency_weighted_jaccard(orig_counter, user_counter)
        set_jaccard = self.set_jaccard_similarity(set(orig_counter), set(user_counter))
        hybrid_similarity = 0.5 * freq_jaccard + 0.5 * set_jaccard
        # Change impact: classes with largest count difference
        change_impact = []
        all_classes = set(orig_counter) | set(user_counter)
        for cls in all_classes:
            diff = abs(orig_counter.get(cls, 0) - user_counter.get(cls, 0))
            if diff > 0:
                change_impact.append({
                    'class': cls,
                    'original_count': orig_counter.get(cls, 0),
                    'user_count': user_counter.get(cls, 0),
                    'count_diff': diff,
                    'original_locations': orig_locations.get(cls, []),
                    'user_locations': user_locations.get(cls, [])
                })
        change_impact.sort(key=lambda x: x['count_diff'], reverse=True)
        result = {
            'original_classes': dict(orig_counter),
            'user_classes': dict(user_counter),
            'shared_classes': list(shared_classes),
            'only_in_original': list(only_in_original),
            'only_in_user': list(only_in_user),
            'frequency_weighted_jaccard': freq_jaccard,
            'set_jaccard': set_jaccard,
            'hybrid_similarity': hybrid_similarity,
            'change_impact': change_impact,
            'original_locations': orig_locations,
            'user_locations': user_locations
        }
        return result

    def parse_config(self, config_path: str) -> Dict[str, Any]:
        """Parse tailwind.config.js using Node.js and return as dict."""
        node_script_path = config_path.replace('\\', '\\\\')
        node_script = f"""
        const config = require('{node_script_path}');
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
        """Extract theme extensions (colors, spacing, fontSize, etc.) from both theme and theme.extend."""
        theme = config.get('theme', {}) if isinstance(config, dict) else {}
        extend = theme.get('extend', {}) if isinstance(theme, dict) else {}
        extensions = {}
        for key in ['colors', 'spacing', 'fontSize', 'borderRadius', 'boxShadow', 'fontFamily', 'screens']:
            # Prefer extend, but include top-level if present
            if key in theme:
                extensions[key] = theme[key]
            if key in extend:
                # If both exist, merge dicts (extend overrides top-level)
                if key in extensions and isinstance(extensions[key], dict) and isinstance(extend[key], dict):
                    merged = {**extensions[key], **extend[key]}
                    extensions[key] = merged
                else:
                    extensions[key] = extend[key]
        return extensions

    def compare_configs(self, original_path: str, user_path: str) -> Dict[str, Any]:
        """Compare two Tailwind config files with partial subkey match (fraction of matching subkey names)."""
        orig_cfg = self.parse_config(original_path)
        user_cfg = self.parse_config(user_path)
        orig_ext = self.extract_theme_extensions(orig_cfg)
        user_ext = self.extract_theme_extensions(user_cfg)
        print(f"[DEBUG] Original extension keys: {list(orig_ext.keys())}")
        print(f"[DEBUG] User extension keys: {list(user_ext.keys())}")
        orig_keys = set(orig_ext.keys())
        user_keys = set(user_ext.keys())
        key_intersection = orig_keys & user_keys
        key_union = orig_keys | user_keys
        print(f"[DEBUG] Key intersection: {key_intersection}")
        print(f"[DEBUG] Key union: {key_union}")
        key_similarity = len(key_intersection) / len(key_union) if key_union else 1.0
        # Detailed per-extension diff and subkey similarity (partial match)
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
                print(f"[DEBUG] For extension '{ext_key}':")
                print(f"  Original subkeys: {orig_subkeys}")
                print(f"  User subkeys: {user_subkeys}")
                print(f"  Shared subkeys: {shared_subkeys}")
                subkey_union = orig_subkeys | user_subkeys
                subkey_intersection = shared_subkeys
                subkey_similarity = len(subkey_intersection) / len(subkey_union) if subkey_union else 1.0
                print(f"  Subkey similarity: {subkey_similarity}")
                per_extension_similarity[ext_key] = subkey_similarity
                subkey_similarities.append(subkey_similarity)
                only_in_original = {k: orig_val[k] for k in orig_subkeys - user_subkeys}
                only_in_user = {k: user_val[k] for k in user_subkeys - orig_subkeys}
                shared_config_values[ext_key] = {
                    'shared_keys': list(shared_subkeys),
                    'only_in_original': only_in_original,  # subkeys only in original config
                    'only_in_user': only_in_user           # subkeys only in user/modified config
                }
            else:
                shared_config_values[ext_key] = {
                    'original_value': orig_val,
                    'user_value': user_val,
                    'equal': orig_val == user_val
                }
                per_extension_similarity[ext_key] = 1.0 if orig_val == user_val else 0.0
                subkey_similarities.append(per_extension_similarity[ext_key])
        all_similarities = [key_similarity] + subkey_similarities if subkey_similarities else [key_similarity]
        improved_config_similarity = sum(all_similarities) / len(all_similarities) if all_similarities else 1.0
        print(f"[DEBUG] key_similarity: {key_similarity}")
        print(f"[DEBUG] subkey_similarities: {subkey_similarities}")
        print(f"[DEBUG] improved_config_similarity: {improved_config_similarity}")
        if improved_config_similarity == 0.0:
            print("[DEBUG] Config similarity is 0.0 because there are no shared extension keys or subkeys.")
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
        return result 