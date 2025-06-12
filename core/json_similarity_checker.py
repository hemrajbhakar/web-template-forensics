import json
import re
from difflib import SequenceMatcher
from typing import Dict, Any, Tuple

def normalize_version(version: str) -> str:
    """Normalize version strings for comparison (e.g., ^1.0.0 -> 1.0.0)."""
    if not isinstance(version, str):
        return str(version)
    return re.sub(r'^[\^~><= ]+', '', version.strip())

def jaccard_similarity(set1, set2):
    set1, set2 = set(set1), set(set2)
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)

def fuzzy_string_similarity(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()

def compare_dependencies(dep1: Dict[str, str], dep2: Dict[str, str]) -> float:
    """Compare dependency dicts by name and normalized version, with boilerplate exclusion for key similarity."""
    boilerplate = {'react', 'react-dom', 'next'}
    names1 = set(dep1.keys())
    names2 = set(dep2.keys())
    # Exclude boilerplate for key similarity only
    filtered1 = names1 - boilerplate
    filtered2 = names2 - boilerplate
    key_sim = jaccard_similarity(filtered1, filtered2)
    # For value similarity, use all shared keys (including boilerplate)
    shared = names1 & names2
    def version_score(v1, v2):
        n1 = normalize_version(v1)
        n2 = normalize_version(v2)
        if n1 == n2:
            return 1.0
        # Check for minor bump (e.g., 1.2.3 vs 1.2.4)
        try:
            parts1 = [int(x) for x in n1.split('.') if x.isdigit()]
            parts2 = [int(x) for x in n2.split('.') if x.isdigit()]
            if len(parts1) == len(parts2) and len(parts1) >= 2:
                # Only last part differs by 1
                if parts1[:-1] == parts2[:-1] and abs(parts1[-1] - parts2[-1]) == 1:
                    return 0.3
        except Exception:
            pass
        return 0.0
    if not shared:
        return key_sim
    value_sim = sum(version_score(dep1[n], dep2[n]) for n in shared) / len(shared)
    # Weighted: 30% key, 70% value
    return 0.3 * key_sim + 0.7 * value_sim

def compare_scripts(s1: Dict[str, str], s2: Dict[str, str]) -> float:
    boilerplate_scripts = {'dev', 'build', 'start', 'lint'}
    # Filter out boilerplate scripts
    filtered1 = {k: v for k, v in s1.items() if k not in boilerplate_scripts}
    filtered2 = {k: v for k, v in s2.items() if k not in boilerplate_scripts}
    keys1 = set(filtered1.keys())
    keys2 = set(filtered2.keys())
    key_sim = jaccard_similarity(keys1, keys2)
    shared = keys1 & keys2
    if not shared:
        return key_sim
    cmd_sim = sum(fuzzy_string_similarity(filtered1[k], filtered2[k]) for k in shared) / len(shared)
    return 0.6 * key_sim + 0.4 * cmd_sim

def compare_metadata(meta1: Dict[str, Any], meta2: Dict[str, Any]) -> float:
    def normalize_str(s):
        return str(s or '').strip().lower()
    def normalize_list(lst):
        return [normalize_str(x) for x in lst]
    keys = ['name', 'version', 'description', 'keywords', 'author']
    scores = []
    for k in keys:
        v1 = meta1.get(k)
        v2 = meta2.get(k)
        if isinstance(v1, list) and isinstance(v2, list):
            scores.append(jaccard_similarity(normalize_list(v1), normalize_list(v2)))
        else:
            n1 = normalize_str(v1)
            n2 = normalize_str(v2)
            scores.append(1.0 if n1 == n2 and n1 != '' else 0.0)
    return sum(scores) / len(scores) if scores else 1.0

def compare_config_blocks(j1: Dict[str, Any], j2: Dict[str, Any]) -> float:
    # Compare config blocks like eslintConfig, browserslist, jest, etc.
    config_keys = set(j1.keys()) & set(j2.keys())
    config_keys = [k for k in config_keys if k.endswith('Config') or k in ['browserslist', 'jest']]
    if not config_keys:
        return 1.0
    scores = []
    for k in config_keys:
        v1, v2 = j1[k], j2[k]
        if isinstance(v1, dict) and isinstance(v2, dict):
            scores.append(jaccard_similarity(v1.keys(), v2.keys()))
        elif isinstance(v1, list) and isinstance(v2, list):
            scores.append(jaccard_similarity(v1, v2))
        else:
            scores.append(fuzzy_string_similarity(str(v1), str(v2)))
    return sum(scores) / len(scores)

def package_json_similarity(pkg1: Dict[str, Any], pkg2: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
    def missing_in_both(key):
        return key not in pkg1 and key not in pkg2

    dep_sim = None if missing_in_both('dependencies') else compare_dependencies(pkg1.get('dependencies', {}), pkg2.get('dependencies', {}))
    dev_sim = None if missing_in_both('devDependencies') else compare_dependencies(pkg1.get('devDependencies', {}), pkg2.get('devDependencies', {}))
    peer_sim = None if missing_in_both('peerDependencies') else compare_dependencies(pkg1.get('peerDependencies', {}), pkg2.get('peerDependencies', {}))
    scripts_sim = None if missing_in_both('scripts') else compare_scripts(pkg1.get('scripts', {}), pkg2.get('scripts', {}))
    meta_sim = None if all(k not in pkg1 and k not in pkg2 for k in ['name', 'version', 'description', 'keywords', 'author']) else compare_metadata(pkg1, pkg2)
    config_sim = None
    config_keys = [k for k in pkg1.keys() if k.endswith('Config') or k in ['browserslist', 'jest']]
    config_keys2 = [k for k in pkg2.keys() if k.endswith('Config') or k in ['browserslist', 'jest']]
    if config_keys or config_keys2:
        config_sim = compare_config_blocks(pkg1, pkg2)

    # Updated weights: scripts weight is now 0.05
    weights = [0.5, 0.2, 0.05, 0.05, 0.05, 0.05]
    sims = [dep_sim, dev_sim, peer_sim, scripts_sim, meta_sim, config_sim]
    section_names = ['dependencies', 'devDependencies', 'peerDependencies', 'scripts', 'meta', 'config']

    dep_weight = weights[0]
    for i, (sim, w, name) in enumerate(zip(sims, weights, section_names)):
        if sim is None and name != 'dependencies':
            dep_weight += w
            weights[i] = 0.0
    weights[0] = dep_weight

    present = [(s, w) for s, w in zip(sims, weights) if s is not None and w > 0]
    if not present:
        overall = None
    else:
        total_weight = sum(w for s, w in present)
        overall = sum(s * w for s, w in present) / total_weight if total_weight > 0 else None
    details = {
        'dependencies_similarity': dep_sim,
        'devDependencies_similarity': dev_sim,
        'peerDependencies_similarity': peer_sim,
        'scripts_similarity': scripts_sim,
        'meta_similarity': meta_sim,
        'config_similarity': config_sim,
        'dependencies_weight': dep_weight
    }
    return overall, details

def compare_compiler_options(opt1: Dict[str, Any], opt2: Dict[str, Any]) -> float:
    keys1 = set(opt1.keys())
    keys2 = set(opt2.keys())
    key_sim = jaccard_similarity(keys1, keys2)
    shared = keys1 & keys2
    if not shared:
        return key_sim
    value_sim = sum(
        1.0 if str(opt1[k]).lower() == str(opt2[k]).lower() else 0.7
        for k in shared
    ) / len(shared)
    return 0.6 * key_sim + 0.4 * value_sim

def compare_include_exclude(ts1: Dict[str, Any], ts2: Dict[str, Any]) -> float:
    arr1 = ts1.get('include', []) + ts1.get('exclude', [])
    arr2 = ts2.get('include', []) + ts2.get('exclude', [])
    return jaccard_similarity(arr1, arr2)

def compare_paths_and_extends(ts1: Dict[str, Any], ts2: Dict[str, Any]) -> float:
    paths1 = ts1.get('compilerOptions', {}).get('paths', {})
    paths2 = ts2.get('compilerOptions', {}).get('paths', {})
    paths_sim = jaccard_similarity(paths1.keys(), paths2.keys()) if paths1 and paths2 else 1.0
    base1 = ts1.get('compilerOptions', {}).get('baseUrl', '')
    base2 = ts2.get('compilerOptions', {}).get('baseUrl', '')
    base_sim = fuzzy_string_similarity(str(base1), str(base2))
    ext1 = ts1.get('extends', '')
    ext2 = ts2.get('extends', '')
    ext_sim = fuzzy_string_similarity(str(ext1), str(ext2))
    return (paths_sim + base_sim + ext_sim) / 3

def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def tsconfig_json_similarity(ts1: Dict[str, Any], ts2: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
    # Only consider compilerOptions for similarity
    co1 = ts1.get('compilerOptions', {})
    co2 = ts2.get('compilerOptions', {})
    flat1 = flatten_dict(co1)
    flat2 = flatten_dict(co2)
    all_keys = set(flat1.keys()) | set(flat2.keys())
    if not all_keys:
        return 1.0, {}
    matched = 0
    details = {}
    for k in all_keys:
        v1 = flat1.get(k, None)
        v2 = flat2.get(k, None)
        if v1 is not None and v2 is not None:
            if str(v1).strip().lower() == str(v2).strip().lower():
                details[k] = 1.0
                matched += 1
            else:
                details[k] = 0.0
        else:
            details[k] = 0.0
    score = matched / len(all_keys)
    return score, details

def load_json_file(path: str) -> Dict[str, Any]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def find_json_file(root: str, filename: str) -> str:
    import os
    for dirpath, _, files in os.walk(root):
        if filename in files:
            return os.path.join(dirpath, filename)
    return ''

def analyze_json_similarity(orig_root: str, mod_root: str) -> Dict[str, Any]:
    result = {}
    # package.json
    orig_pkg = find_json_file(orig_root, 'package.json')
    mod_pkg = find_json_file(mod_root, 'package.json')
    if orig_pkg and mod_pkg:
        pkg1 = load_json_file(orig_pkg)
        pkg2 = load_json_file(mod_pkg)
        pkg_score, pkg_details = package_json_similarity(pkg1, pkg2)
        result['package_json'] = pkg_score
        result['package_json_details'] = pkg_details
    else:
        result['package_json'] = None
        result['package_json_details'] = {}
    # tsconfig.json
    orig_ts = find_json_file(orig_root, 'tsconfig.json')
    mod_ts = find_json_file(mod_root, 'tsconfig.json')
    if orig_ts and mod_ts:
        ts1 = load_json_file(orig_ts)
        ts2 = load_json_file(mod_ts)
        ts_score, ts_details = tsconfig_json_similarity(ts1, ts2)
        result['tsconfig_json'] = ts_score
        result['tsconfig_json_details'] = ts_details
    else:
        result['tsconfig_json'] = None
        result['tsconfig_json_details'] = {}
    return result 