import os
import zipfile
import tempfile
from collections import defaultdict, Counter
from typing import List, Dict, Tuple
import difflib
import signal
import numpy as np
# --- New imports for structure matching ---
from .html_parser import HTMLParser
from .structure_comparator import StructureComparator
from .css_style_checker import CSSStyleChecker
from .tailwind_analyzer import TailwindAnalyzer
from .jsx_treesitter_parser import parse_jsx_with_treesitter

# --- Step 1: Unzip & list files ---
def unzip_to_tempdir(zip_path: str) -> str:
    """Unzips a zip file to a temporary directory and returns the path."""
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    return temp_dir

def list_files_by_type(root_dir: str) -> Dict[str, List[str]]:
    """Recursively list files by type (html, css, jsx/tsx) with relative paths from root_dir. Skip all other file types."""
    file_types = defaultdict(list)
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            rel_path = os.path.relpath(os.path.join(dirpath, fname), root_dir)
            ext = os.path.splitext(fname)[1].lower()
            if ext == '.html':
                file_types['html'].append(rel_path)
            elif ext == '.css':
                file_types['css'].append(rel_path)
            elif ext in ('.jsx', '.tsx'):
                file_types['jsx'].append(rel_path)
            elif fname == 'tailwind.config.js':
                file_types['tailwind_config'].append(rel_path)
            # Skip all other files
    return dict(file_types)

# --- Step 2: Exact path-based match ---
def exact_path_match(files1: List[str], files2: List[str]) -> Tuple[List[Tuple[str, str]], List[str], List[str]]:
    """Return exact matches and remaining unmatched files."""
    set2 = set(files2)
    matches = []
    unmatched1 = []
    unmatched2 = set2.copy()
    for f1 in files1:
        if f1 in set2:
            matches.append((f1, f1))
            unmatched2.remove(f1)
        else:
            unmatched1.append(f1)
    return matches, unmatched1, list(unmatched2)

# --- Step 3: Fuzzy filename match ---
def fuzzy_filename_match(files1: List[str], files2: List[str], threshold: float = 0.75) -> Tuple[List[Tuple[str, str, float]], List[str], List[str]]:
    """Fuzzy match files by filename (not path). Returns matches with score, and remaining unmatched."""
    used2 = set()
    matches = []
    for f1 in files1:
        fname1 = os.path.basename(f1)
        best_score = 0
        best_f2 = None
        for f2 in files2:
            if f2 in used2:
                continue
            fname2 = os.path.basename(f2)
            score = difflib.SequenceMatcher(None, fname1, fname2).ratio()
            if score > best_score:
                best_score = score
                best_f2 = f2
        if best_score >= threshold and best_f2:
            matches.append((f1, best_f2, best_score))
            used2.add(best_f2)
    unmatched1 = [f1 for f1 in files1 if all(f1 != m[0] for m in matches)]
    unmatched2 = [f2 for f2 in files2 if f2 not in used2]
    return matches, unmatched1, unmatched2

# --- Step 4: AST/structure match (stub) ---
def structure_match_stub(files1: List[str], files2: List[str]) -> List[Tuple[str, str, float]]:
    """Stub for AST/structure-based matching. To be implemented."""
    # Placeholder: returns empty list
    return []

# --- Step 5: Contextual match (stub) ---
def contextual_match_stub(files1: List[str], files2: List[str]) -> List[Tuple[str, str, float]]:
    """Stub for contextual folder-based matching. To be implemented."""
    # Placeholder: returns empty list
    return []

# --- Step 6: Output JSON ---
def output_matched_pairs_json(exact, fuzzy, structure, contextual, filetype) -> List[Dict]:
    """Combine all matches into a JSON list for the given filetype."""
    result = []
    for orig, mod in exact:
        result.append({
            'original': orig,
            'modified': mod,
            'score': 1.0,
            'match_type': 'exact'
        })
    for orig, mod, score in fuzzy:
        result.append({
            'original': orig,
            'modified': mod,
            'score': round(score, 2),
            'match_type': 'fuzzy'
        })
    for orig, mod, score in structure:
        result.append({
            'original': orig,
            'modified': mod,
            'score': round(score, 2),
            'match_type': 'fuzzy+structure'
        })
    for orig, mod, score in contextual:
        result.append({
            'original': orig,
            'modified': mod,
            'score': round(score, 2),
            'match_type': 'contextual'
        })
    return result

def structure_match_html(unmatched1: List[str], unmatched2: List[str], dir1: str, dir2: str, threshold: float = 0.5) -> List[Tuple[str, str, float]]:
    """Structure-based matching for HTML files using StructureComparator."""
    parser = HTMLParser()
    comparator = StructureComparator()
    matches = []
    used2 = set()
    for f1 in unmatched1:
        best_score = 0
        best_f2 = None
        tree1 = parser.parse_file(os.path.join(dir1, f1))
        for f2 in unmatched2:
            if f2 in used2:
                continue
            tree2 = parser.parse_file(os.path.join(dir2, f2))
            score = comparator.compare_structures(tree1, tree2).similarity_score
            if score > best_score:
                best_score = score
                best_f2 = f2
        if best_score >= threshold and best_f2:
            matches.append((f1, best_f2, best_score))
            used2.add(best_f2)
    return matches

def structure_match_css(unmatched1: List[str], unmatched2: List[str], dir1: str, dir2: str, threshold: float = 0.5) -> List[Tuple[str, str, float]]:
    """Structure-based matching for CSS files using CSSStyleChecker."""
    checker = CSSStyleChecker()
    matches = []
    used2 = set()
    for f1 in unmatched1:
        best_score = 0
        best_f2 = None
        with open(os.path.join(dir1, f1), 'r', encoding='utf-8') as f:
            css1 = f.read()
        for f2 in unmatched2:
            if f2 in used2:
                continue
            with open(os.path.join(dir2, f2), 'r', encoding='utf-8') as f:
                css2 = f.read()
            score = checker.compare_css(css1, css2)["css_similarity"]
            if score > best_score:
                best_score = score
                best_f2 = f2
        if best_score >= threshold and best_f2:
            matches.append((f1, best_f2, best_score))
            used2.add(best_f2)
    return matches

def structure_match_jsx(unmatched1: List[str], unmatched2: List[str], dir1: str, dir2: str, threshold: float = 0.5) -> List[Tuple[str, str, float]]:
    """Structure-based matching for JSX/TSX files using StructureComparator and Node.js tree-sitter parser."""
    comparator = StructureComparator()
    matches = []
    used2 = set()
    for f1 in unmatched1:
        best_score = 0
        best_f2 = None
        tree1 = parse_jsx_with_treesitter(os.path.join(dir1, f1))
        for f2 in unmatched2:
            if f2 in used2:
                continue
            tree2 = parse_jsx_with_treesitter(os.path.join(dir2, f2))
            score = comparator.compare_structures(tree1, tree2).similarity_score
            if score > best_score:
                best_score = score
                best_f2 = f2
        if best_score >= threshold and best_f2:
            matches.append((f1, best_f2, best_score))
            used2.add(best_f2)
    return matches

# Replace structure_match_stub with dispatcher

def structure_match(files1: List[str], files2: List[str], dir1: str, dir2: str, filetype: str, threshold: float = 0.5) -> List[Tuple[str, str, float]]:
    """Dispatch structure matching based on filetype."""
    if filetype == 'html':
        return structure_match_html(files1, files2, dir1, dir2, threshold)
    elif filetype == 'jsx':
        return structure_match_jsx(files1, files2, dir1, dir2, threshold)
    elif filetype == 'css':
        return structure_match_css(files1, files2, dir1, dir2, threshold)
    else:
        return []

def contextual_match(files1: List[str], files2: List[str], matched_pairs: List[Tuple[str, str]], threshold: float = 0.5) -> List[Tuple[str, str, float]]:
    """Contextual matching using folder hierarchy and neighboring file similarity."""
    used2 = set([mod for _, mod, *_ in matched_pairs])
    matches = []
    for f1 in files1:
        best_score = 0
        best_f2 = None
        f1_parts = f1.split(os.sep)
        for f2 in files2:
            if f2 in used2:
                continue
            f2_parts = f2.split(os.sep)
            # Folder hierarchy similarity: count matching parent folders
            folder_score = 0
            for a, b in zip(f1_parts[:-1], f2_parts[:-1]):
                if a == b:
                    folder_score += 1
                else:
                    break
            folder_score = folder_score / max(len(f1_parts), len(f2_parts))
            # Neighboring file similarity: count how many siblings are already matched
            f1_parent = os.sep.join(f1_parts[:-1])
            f2_parent = os.sep.join(f2_parts[:-1])
            neighbor_score = 0
            for orig, mod, *_ in matched_pairs:
                if orig.startswith(f1_parent) and mod.startswith(f2_parent):
                    neighbor_score += 1
            neighbor_score = neighbor_score / (len(matched_pairs) + 1)
            score = 0.7 * folder_score + 0.3 * neighbor_score
            if score > best_score:
                best_score = score
                best_f2 = f2
        if best_score >= threshold and best_f2:
            matches.append((f1, best_f2, best_score))
            used2.add(best_f2)
    return matches

def get_prediction(score):
    if score >= 0.75:
        return "High similarity — likely copied or derived"
    elif score >= 0.40:
        return "Moderate similarity — possible reuse or inspiration"
    else:
        return "Low similarity — likely independent"

def content_similarity(a: str, b: str) -> float:
    """Compute text similarity between two strings using difflib."""
    return difflib.SequenceMatcher(None, a, b).ratio()

def content_match_css(unmatched1: List[str], unmatched2: List[str], dir1: str, dir2: str, threshold: float = 0.6) -> List[Tuple[str, str, float]]:
    """Content similarity matching for unmatched CSS files."""
    matches = []
    used2 = set()
    for f1 in unmatched1:
        best_score = 0
        best_f2 = None
        with open(os.path.join(dir1, f1), 'r', encoding='utf-8') as file1:
            css1 = file1.read()
        for f2 in unmatched2:
            if f2 in used2:
                continue
            with open(os.path.join(dir2, f2), 'r', encoding='utf-8') as file2:
                css2 = file2.read()
            score = content_similarity(css1, css2)
            if score > best_score:
                best_score = score
                best_f2 = f2
        if best_score >= threshold and best_f2:
            matches.append((f1, best_f2, best_score))
            used2.add(best_f2)
    return matches

def handler(signum, frame):
    raise TimeoutError("Timed out during file comparison!")

# --- Main orchestrator for full matching and comparison workflow ---
def match_and_compare_all(original_dir: str, modified_dir: str) -> Dict:
    print('--- [LOG] Starting match_and_compare_all ---')
    file_types = ['html', 'css', 'jsx']
    results = {}
    total_files_compared = Counter()
    all_scores = []
    unmatched_files = {ftype: {'original': [], 'modified': []} for ftype in file_types}
    files_matched = {ftype: 0 for ftype in file_types}
    files_unmatched = {ftype: 0 for ftype in file_types}
    files_compared = {ftype: 0 for ftype in file_types}
    predictions = {}
    tailwind_results = []
    tailwind_scores = []
    tailwind_analyzer = TailwindAnalyzer()
    print('--- [LOG] Starting file matching ---')
    for filetype in file_types:
        files1 = list_files_by_type(original_dir).get(filetype, [])
        files2 = list_files_by_type(modified_dir).get(filetype, [])
        print(f'--- [LOG] {filetype}: {len(files1)} original, {len(files2)} modified files ---')
        # Step 2: Exact match
        exact, rem1, rem2 = exact_path_match(files1, files2)
        # Step 3: Fuzzy match
        fuzzy, rem1, rem2 = fuzzy_filename_match(rem1, rem2)
        # Step 4: Structure match
        structure = structure_match(rem1, rem2, original_dir, modified_dir, filetype)
        # Step 5: Contextual match
        contextual = contextual_match(rem1, rem2, exact + fuzzy + structure)
        # Step 5.5: Content similarity match for CSS only
        content_matches = []
        if filetype == 'css':
            matched1 = set([m[0] for m in structure + contextual])
            matched2 = set([m[1] for m in structure + contextual])
            unmatched1 = [f for f in rem1 if f not in matched1]
            unmatched2 = [f for f in rem2 if f not in matched2]
            content_matches = content_match_css(unmatched1, unmatched2, original_dir, modified_dir)
        print(f'--- [LOG] {filetype}: file matching done ---')
        # Step 6: Output matched pairs
        matched_pairs = output_matched_pairs_json(exact, fuzzy, structure, contextual, filetype)
        if filetype == 'css' and content_matches:
            for orig, mod, score in content_matches:
                matched_pairs.append({
                    'original': orig,
                    'modified': mod,
                    'score': round(score, 2),
                    'match_type': 'content'
                })
        matched_originals = set([m['original'] for m in matched_pairs])
        matched_modifieds = set([m['modified'] for m in matched_pairs])
        unmatched_files[filetype]['original'] = [f for f in files1 if f not in matched_originals]
        unmatched_files[filetype]['modified'] = [f for f in files2 if f not in matched_modifieds]
        print(f'--- [LOG] {filetype}: starting pairwise comparison ---')
        checker = None
        for pair in matched_pairs:
            if filetype == 'html':
                parser = HTMLParser()
                comparator = StructureComparator()
                orig_path = os.path.join(original_dir, pair['original'])
                mod_path = os.path.join(modified_dir, pair['modified'])
                tree1 = parser.parse_file(orig_path)
                tree2 = parser.parse_file(mod_path)
                comp_result = comparator.compare_structures(tree1, tree2)
                pair['similarity'] = round(comp_result.similarity_score, 2)
                pair['details'] = comp_result.to_dict()
                all_scores.append(comp_result.similarity_score)
            elif filetype == 'css':
                checker = CSSStyleChecker()
                orig_path = os.path.join(original_dir, pair['original'])
                mod_path = os.path.join(modified_dir, pair['modified'])
                with open(orig_path, 'r', encoding='utf-8') as f:
                    css1 = f.read()
                with open(mod_path, 'r', encoding='utf-8') as f:
                    css2 = f.read()
                comp_result = checker.compare_css(css1, css2)
                pair['similarity'] = comp_result['css_similarity']
                pair['details'] = comp_result
                all_scores.append(comp_result['css_similarity'])
            elif filetype == 'jsx':
                print(f'--- [LOG] JSX: Starting comparison for {pair["original"]} and {pair["modified"]} ---')
                comparator = StructureComparator()
                orig_path = os.path.join(original_dir, pair['original'])
                mod_path = os.path.join(modified_dir, pair['modified'])
                print(f'--- [LOG] JSX: Parsing original {orig_path} ---')
                tree1 = parse_jsx_with_treesitter(orig_path)
                print(f'--- [LOG] JSX: Finished parsing original {orig_path} ---')
                print(f'--- [LOG] JSX: Parsing modified {mod_path} ---')
                tree2 = parse_jsx_with_treesitter(mod_path)
                print(f'--- [LOG] JSX: Finished parsing modified {mod_path} ---')
                print(f'--- [LOG] JSX: Starting structure comparison ---')
                comp_result = comparator.compare_structures(tree1, tree2)
                print(f'--- [LOG] JSX: Finished structure comparison ---')
                pair['similarity'] = round(comp_result.similarity_score, 2)
                pair['details'] = comp_result.to_dict()
                all_scores.append(comp_result.similarity_score)
                print(f'--- [LOG] JSX: Finished comparison for {pair["original"]} and {pair["modified"]} ---')
            # Tailwind class comparison for HTML and JSX
            if filetype in ('html', 'jsx'):
                orig_path = os.path.join(original_dir, pair['original'])
                mod_path = os.path.join(modified_dir, pair['modified'])
                with open(orig_path, 'r', encoding='utf-8') as f:
                    orig_content = f.read()
                with open(mod_path, 'r', encoding='utf-8') as f:
                    mod_content = f.read()
                tw_result = tailwind_analyzer.compare_classes(orig_content, mod_content, filetype)
                tw_result['file_pair'] = {'original': pair['original'], 'modified': pair['modified']}
                tw_result['similarity'] = tw_result.get('hybrid_similarity', 0.0)
                tw_result['match_type'] = pair.get('match_type', 'matched')
                if tw_result['original_classes'] or tw_result['user_classes']:
                    tailwind_results.append(tw_result)
                    tailwind_scores.append(tw_result['hybrid_similarity'])
                    if 'set_jaccard_scores' not in locals():
                        set_jaccard_scores = []
                        freq_jaccard_scores = []
                        hybrid_scores = []
                        weighted_scores = []
                        total_class_counts = []
                    set_jaccard_scores.append(tw_result.get('set_jaccard', 0.0))
                    freq_jaccard_scores.append(tw_result.get('frequency_weighted_jaccard', 0.0))
                    hybrid_scores.append(tw_result.get('hybrid_similarity', 0.0))
                    total_classes = sum(tw_result['original_classes'].values()) + sum(tw_result['user_classes'].values())
                    weighted_scores.append((tw_result.get('hybrid_similarity', 0.0), total_classes))
                    total_class_counts.append(total_classes)
                # else:
                #     print(f"Skipping {pair['original']} and {pair['modified']} for Tailwind comparison (no classes found)")
        print(f'--- [LOG] {filetype}: pairwise comparison done ---')
        # Step 8: Aggregate (penalize unmatched files)
        num_matched = len(matched_pairs)
        num_unmatched = len(unmatched_files[filetype]['original']) + len(unmatched_files[filetype]['modified'])
        unique_matched = set([(m['original'], m['modified']) for m in matched_pairs])
        total_files = len(files1) + len(files2) - len(unique_matched)
        sim_scores = [pair.get('similarity', pair.get('score', 0.0)) for pair in matched_pairs]
        sim_scores += [0.0] * num_unmatched
        agg_score = sum(sim_scores) / total_files if total_files > 0 else 0.0
        results[filetype] = {
            'files_compared': len(files1),
            'files_matched': num_matched,
            'files_unmatched': num_unmatched,
            'matched_pairs': matched_pairs,
            'unmatched_files': unmatched_files[filetype],
            'aggregate_score': round(agg_score, 3)
        }
        predictions[filetype] = get_prediction(agg_score)
    print('--- [LOG] Aggregation and scoring done ---')
    # --- Aggregation: file-count-based weighting ---
    similarities = []
    # HTML
    for r in results.get('html', {}).get('matched_pairs', []):
        similarities.append(r.get('similarity', r.get('score', 0.0)))
    # JSX
    for r in results.get('jsx', {}).get('matched_pairs', []):
        similarities.append(r.get('similarity', r.get('score', 0.0)))
    # CSS
    for r in results.get('css', {}).get('matched_pairs', []):
        similarities.append(r.get('similarity', r.get('score', 0.0)))
    # Tailwind classes
    for r in tailwind_results:
        similarities.append(r['similarity'])
    # Tailwind config (as a virtual file, if present)
    config_sim = results.get('tailwind', {}).get('config_similarity', None)
    if config_sim is not None:
        similarities.append(config_sim)
    # Compute file-count-weighted average
    if similarities:
        overall_similarity = sum(similarities) / len(similarities)
    else:
        overall_similarity = 0.0
    results['overall_similarity'] = overall_similarity
    results['prediction'] = {
        'overall_match_quality': get_prediction(overall_similarity),
        'html_prediction': predictions.get('html', ''),
        'css_prediction': predictions.get('css', ''),
        'jsx_prediction': predictions.get('jsx', '')
    }
    print('--- [LOG] Preparing Tailwind aggregation ---')
    # Ensure these are always defined, even if no tailwind_results
    shared_classes = set()
    only_in_original = set()
    only_in_user = set()
    change_impact_all = []
    tailwind_similarity = sum(tailwind_scores) / len(tailwind_scores) if tailwind_scores else 1.0
    set_jaccard_avg = sum(set_jaccard_scores) / len(set_jaccard_scores) if 'set_jaccard_scores' in locals() and set_jaccard_scores else 1.0
    freq_jaccard_avg = sum(freq_jaccard_scores) / len(freq_jaccard_scores) if 'freq_jaccard_scores' in locals() and freq_jaccard_scores else 1.0
    # Median and percent above 0.9
    median_similarity = float(np.median(hybrid_scores)) if 'hybrid_scores' in locals() and hybrid_scores else 1.0
    percent_above_90 = sum(1 for s in hybrid_scores if s >= 0.9) / len(hybrid_scores) if 'hybrid_scores' in locals() and hybrid_scores else 1.0
    # Weighted average (by total class count per file)
    weighted_sum = sum(score * weight for score, weight in weighted_scores) if 'weighted_scores' in locals() and weighted_scores else 0.0
    total_weight = sum(weight for _, weight in weighted_scores) if 'weighted_scores' in locals() and weighted_scores else 0.0
    weighted_avg = weighted_sum / total_weight if total_weight > 0 else 1.0
    # Ignore files with only a single class difference if the rest are identical (soft aggregation)
    filtered_scores = [r['hybrid_similarity'] for r in tailwind_results if not (len(r['change_impact']) == 1 and r['change_impact'][0]['count_diff'] == 1)]
    soft_avg = sum(filtered_scores) / len(filtered_scores) if filtered_scores else tailwind_similarity
    # Print/log per-file/component similarity table
    print("\nTailwind Per-File Similarity Table:")
    print(f"{'Original':30} {'Modified':30} {'Hybrid':>8} {'SetJac':>8} {'FreqJac':>8} TotalClasses")
    for r in tailwind_results:
        o = r['file_pair']['original']
        m = r['file_pair']['modified']
        h = r.get('hybrid_similarity', 0.0)
        sj = r.get('set_jaccard', 0.0)
        fj = r.get('frequency_weighted_jaccard', 0.0)
        tc = sum(r['original_classes'].values()) + sum(r['user_classes'].values())
        print(f"{o:30} {m:30} {h:8.2f} {sj:8.2f} {fj:8.2f} {tc:11}")
    results['tailwind'] = {
        'class_similarity': tailwind_similarity,
        'set_jaccard': set_jaccard_avg,
        'frequency_weighted_jaccard': freq_jaccard_avg,
        'median_similarity': median_similarity,
        'percent_files_above_90': percent_above_90,
        'weighted_average': weighted_avg,
        'soft_average': soft_avg,
        'shared_classes': list(shared_classes),
        'only_in_original': list(only_in_original),
        'only_in_user': list(only_in_user),
        'per_file_results': tailwind_results,
        'change_impact': change_impact_all
    }
    # Final debug prints for tracing
    print("DEBUG: Final tailwind_similarity =", tailwind_similarity)
    print("DEBUG: tailwind_scores =", tailwind_scores)
    print("DEBUG: results['tailwind'] =", results['tailwind'])
    print('--- [LOG] Tailwind aggregation done ---')
    def aggregate_html_summary(pairs):
        total = matching = different = missing = extra = 0
        for pair in pairs:
            summary = pair.get('details', {}).get('summary', {}).get('html', {})
            total += summary.get('total_elements', 0)
            matching += summary.get('matching_elements', 0)
            different += summary.get('different_elements', 0)
            missing += summary.get('missing_elements', 0)
            extra += summary.get('extra_elements', 0)
        return {
            'total_elements': total,
            'matching_elements': matching,
            'different_elements': different,
            'missing_elements': missing,
            'extra_elements': extra
        }
    def aggregate_jsx_summary(pairs):
        total = matching = different = missing = extra = 0
        for pair in pairs:
            summary = pair.get('details', {}).get('summary', {}).get('jsx', {})
            total += summary.get('total_elements', 0)
            matching += summary.get('matching_elements', 0)
            different += summary.get('different_elements', 0)
            missing += summary.get('missing_elements', 0)
            extra += summary.get('extra_elements', 0)
        return {
            'total_elements': total,
            'matching_elements': matching,
            'different_elements': different,
            'missing_elements': missing,
            'extra_elements': extra
        }
    def aggregate_css_summary(pairs):
        total = matching = different = missing = extra = 0
        for pair in pairs:
            details = pair.get('details', {})
            matching += details.get('matching_selectors', 0)
            different += details.get('different_selectors', 0)
            missing += details.get('missing_selectors', 0)
            extra += details.get('extra_selectors', 0)
        total = matching + different + missing + extra
        return {
            'total_selectors': total,
            'matching_selectors': matching,
            'different_selectors': different,
            'missing_selectors': missing,
            'extra_selectors': extra
        }
    results['summary'] = {
        'html': aggregate_html_summary(results.get('html', {}).get('matched_pairs', [])),
        'jsx': aggregate_jsx_summary(results.get('jsx', {}).get('matched_pairs', [])),
        'css': aggregate_css_summary(results.get('css', {}).get('matched_pairs', [])),
        'files_compared': files_compared,
        'files_matched': files_matched,
        'files_unmatched': files_unmatched
    }
    results['similarity_scores'] = {
        'overall': results.get('overall_similarity', 0.0),
        'html': results.get('html', {}).get('aggregate_score', 0.0),
        'jsx': results.get('jsx', {}).get('aggregate_score', 0.0),
        'css': results.get('css', {}).get('aggregate_score', 0.0),
        'tailwind': results.get('tailwind', {}).get('class_similarity', 1.0),
        'tailwind_set_jaccard': results.get('tailwind', {}).get('set_jaccard', 1.0),
        'tailwind_frequency_weighted_jaccard': results.get('tailwind', {}).get('frequency_weighted_jaccard', 1.0)
    }
    print('--- [LOG] Returning results from match_and_compare_all ---')
    # --- Tailwind config comparison (if config files exist) ---
    orig_config_files = list_files_by_type(original_dir).get('tailwind_config', [])
    mod_config_files = list_files_by_type(modified_dir).get('tailwind_config', [])
    config_results = []
    if orig_config_files and mod_config_files:
        for orig_cfg in orig_config_files:
            for mod_cfg in mod_config_files:
                print(f"[DEBUG] Running Tailwind config comparison for: {orig_cfg} vs {mod_cfg}")
                cfg_result = tailwind_analyzer.compare_configs(os.path.join(original_dir, orig_cfg), os.path.join(modified_dir, mod_cfg))
                print(f"[DEBUG] Tailwind config comparison result: improved_config_similarity={cfg_result.get('improved_config_similarity')}, shared_config_keys={cfg_result.get('shared_config_keys')}, only_in_original_config={cfg_result.get('only_in_original_config')}, only_in_user_config={cfg_result.get('only_in_user_config')}")
                config_results.append(cfg_result)
    # --- Aggregate config similarity into results['tailwind'] ---
    if 'tailwind' in results:
        if config_results:
            avg_config_similarity = sum(r.get('improved_config_similarity', 0.0) for r in config_results) / len(config_results)
            results['tailwind']['config_similarity'] = avg_config_similarity
            # Add details from the first config result for UI
            results['tailwind']['shared_config_keys'] = config_results[0].get('shared_config_keys', [])
            results['tailwind']['only_in_original_config'] = config_results[0].get('only_in_original_config', [])
            results['tailwind']['only_in_user_config'] = config_results[0].get('only_in_user_config', [])
            results['tailwind']['shared_config_values'] = config_results[0].get('shared_config_values', {})
        else:
            results['tailwind']['config_similarity'] = 0.0
    return results 