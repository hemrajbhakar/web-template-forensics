import os
import zipfile
import tempfile
from collections import defaultdict, Counter
from typing import List, Dict, Tuple
import difflib
# --- New imports for structure matching ---
from .html_parser import HTMLParser
from .jsx_parser import JSXParser
from .structure_comparator import StructureComparator
from .css_style_checker import CSSStyleChecker

# --- Step 1: Unzip & list files ---
def unzip_to_tempdir(zip_path: str) -> str:
    """Unzips a zip file to a temporary directory and returns the path."""
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    return temp_dir

def list_files_by_type(root_dir: str) -> Dict[str, List[str]]:
    """Recursively list files by type (html, css, jsx/tsx) with relative paths from root_dir."""
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

def structure_match_jsx(unmatched1: List[str], unmatched2: List[str], dir1: str, dir2: str, threshold: float = 0.5) -> List[Tuple[str, str, float]]:
    """Structure-based matching for JSX/TSX files using StructureComparator."""
    parser = JSXParser()
    comparator = StructureComparator()
    matches = []
    used2 = set()
    for f1 in unmatched1:
        best_score = 0
        best_f2 = None
        tree1 = parser.parse_jsx_file(os.path.join(dir1, f1))
        for f2 in unmatched2:
            if f2 in used2:
                continue
            tree2 = parser.parse_jsx_file(os.path.join(dir2, f2))
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

# --- Main orchestrator for full matching and comparison workflow ---
def match_and_compare_all(original_dir: str, modified_dir: str) -> Dict:
    """Run the full matching and comparison workflow for HTML, CSS, and JSX/TSX files."""
    file_types = ['html', 'css', 'jsx']
    results = {}
    total_files_compared = Counter()
    all_scores = []
    unmatched_files = {ftype: {'original': [], 'modified': []} for ftype in file_types}
    files_matched = {ftype: 0 for ftype in file_types}
    files_unmatched = {ftype: 0 for ftype in file_types}
    files_compared = {ftype: 0 for ftype in file_types}
    predictions = {}
    for filetype in file_types:
        files1 = list_files_by_type(original_dir).get(filetype, [])
        files2 = list_files_by_type(modified_dir).get(filetype, [])
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
            # Remove already matched files from rem1/rem2
            matched1 = set([m[0] for m in structure + contextual])
            matched2 = set([m[1] for m in structure + contextual])
            unmatched1 = [f for f in rem1 if f not in matched1]
            unmatched2 = [f for f in rem2 if f not in matched2]
            content_matches = content_match_css(unmatched1, unmatched2, original_dir, modified_dir)
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
        # Unmatched files
        matched_originals = set([m['original'] for m in matched_pairs])
        matched_modifieds = set([m['modified'] for m in matched_pairs])
        unmatched_files[filetype]['original'] = [f for f in files1 if f not in matched_originals]
        unmatched_files[filetype]['modified'] = [f for f in files2 if f not in matched_modifieds]
        # Step 7: Pairwise comparison
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
            elif filetype == 'jsx':
                parser = JSXParser()
                comparator = StructureComparator()
                orig_path = os.path.join(original_dir, pair['original'])
                mod_path = os.path.join(modified_dir, pair['modified'])
                tree1 = parser.parse_jsx_file(orig_path)
                tree2 = parser.parse_jsx_file(mod_path)
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
        # Step 8: Aggregate (penalize unmatched files)
        num_matched = len(matched_pairs)
        num_unmatched = len(unmatched_files[filetype]['original']) + len(unmatched_files[filetype]['modified'])
        unique_matched = set([(m['original'], m['modified']) for m in matched_pairs])
        total_files = len(files1) + len(files2) - len(unique_matched)
        # Gather similarity scores for matched pairs
        sim_scores = [pair.get('similarity', pair.get('score', 0.0)) for pair in matched_pairs]
        # Add 0.0 for each unmatched file
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
    # Step 9: Prepare output JSON for UI
    overall_similarity = round(sum(all_scores) / len(all_scores), 2) if all_scores else 0.0
    results['overall_similarity'] = overall_similarity
    results['prediction'] = {
        'overall_match_quality': get_prediction(overall_similarity),
        'html_prediction': predictions.get('html', ''),
        'css_prediction': predictions.get('css', ''),
        'jsx_prediction': predictions.get('jsx', '')
    }
    # Robust summary aggregation
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
        'css': results.get('css', {}).get('aggregate_score', 0.0)
    }
    return results 