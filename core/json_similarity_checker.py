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
    """Compare dependency dicts by name and normalized version."""
    names1 = set(dep1.keys())
    names2 = set(dep2.keys())
    name_sim = jaccard_similarity(names1, names2)
    # For shared names, compare versions
    shared = names1 & names2
    if not shared:
        return name_sim
    version_sim = sum(
        1.0 if normalize_version(dep1[n]) == normalize_version(dep2[n]) else 0.7
        for n in shared
    ) / len(shared)
    # Weighted: 70% name, 30% version
    return 0.7 * name_sim + 0.3 * version_sim

def compare_scripts(s1: Dict[str, str], s2: Dict[str, str]) -> float:
    keys1 = set(s1.keys())
    keys2 = set(s2.keys())
    key_sim = jaccard_similarity(keys1, keys2)
    # For shared keys, compare command strings
    shared = keys1 & keys2
    if not shared:
        return key_sim
    cmd_sim = sum(fuzzy_string_similarity(s1[k], s2[k]) for k in shared) / len(shared)
    return 0.6 * key_sim + 0.4 * cmd_sim

def compare_metadata(meta1: Dict[str, Any], meta2: Dict[str, Any]) -> float:
    keys = ['name', 'version', 'description', 'keywords', 'author']
    scores = []
    for k in keys:
        v1 = meta1.get(k)
        v2 = meta2.get(k)
        if isinstance(v1, list) and isinstance(v2, list):
            scores.append(jaccard_similarity(v1, v2))
        else:
            scores.append(fuzzy_string_similarity(str(v1 or ''), str(v2 or '')))
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
    dep_sim = compare_dependencies(pkg1.get('dependencies', {}), pkg2.get('dependencies', {}))
    dev_sim = compare_dependencies(pkg1.get('devDependencies', {}), pkg2.get('devDependencies', {}))
    peer_sim = compare_dependencies(pkg1.get('peerDependencies', {}), pkg2.get('peerDependencies', {}))
    scripts_sim = compare_scripts(pkg1.get('scripts', {}), pkg2.get('scripts', {}))
    meta_sim = compare_metadata(pkg1, pkg2)
    config_sim = compare_config_blocks(pkg1, pkg2)
    # Weighted average
    overall = (
        0.5 * dep_sim +
        0.2 * dev_sim +
        0.05 * peer_sim +
        0.15 * scripts_sim +
        0.05 * meta_sim +
        0.05 * config_sim
    )
    details = {
        'dependencies_similarity': dep_sim,
        'devDependencies_similarity': dev_sim,
        'peerDependencies_similarity': peer_sim,
        'scripts_similarity': scripts_sim,
        'meta_similarity': meta_sim,
        'config_similarity': config_sim
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

def tsconfig_json_similarity(ts1: Dict[str, Any], ts2: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
    comp_sim = compare_compiler_options(ts1.get('compilerOptions', {}), ts2.get('compilerOptions', {}))
    inc_exc_sim = compare_include_exclude(ts1, ts2)
    paths_ext_sim = compare_paths_and_extends(ts1, ts2)
    overall = 0.6 * comp_sim + 0.2 * inc_exc_sim + 0.2 * paths_ext_sim
    details = {
        'compiler_options_similarity': comp_sim,
        'include_exclude_similarity': inc_exc_sim,
        'paths_and_extends_similarity': paths_ext_sim
    }
    return overall, details

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