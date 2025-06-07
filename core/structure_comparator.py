"""
Structure Comparator Module
Compares HTML and JSX structures to find similarities and differences.
"""

from typing import Dict, List, Tuple, Set, Optional, Union, Any
import difflib
from dataclasses import dataclass, field
import logging
import json
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class AttributeComparison:
    matching: Dict[str, str] = field(default_factory=dict)
    different: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    missing: Dict[str, str] = field(default_factory=dict)
    extra: Dict[str, str] = field(default_factory=dict)

@dataclass
class ComparisonResult:
    similarity_score: float = 0.0
    matching_elements: List[Tuple[Dict, Dict]] = field(default_factory=list)
    different_elements: List[Tuple[Dict, Optional[Dict]]] = field(default_factory=list)
    missing_elements: List[Dict] = field(default_factory=list)
    extra_elements: List[Dict] = field(default_factory=list)
    attribute_details: Dict[str, AttributeComparison] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert the comparison result to a dictionary format expected by the frontend."""
        total_elements = (len(self.matching_elements) + 
                        len(self.different_elements) + 
                        len(self.missing_elements) + 
                        len(self.extra_elements))
        
        element_counts = {
            'matching_elements': len(self.matching_elements),
            'different_elements': len(self.different_elements),
            'missing_elements': len(self.missing_elements),
            'extra_elements': len(self.extra_elements),
            'total_elements': total_elements
        }
        
        return {
            'similarity_scores': {
                'overall': self.similarity_score,
                'html': self.similarity_score,
                'jsx': self.similarity_score,
            },
            'summary': {
                'html': element_counts.copy(),
                'jsx': element_counts.copy()
            },
            'details': {
                'attribute_details': {k: v.__dict__ for k, v in self.attribute_details.items()}
            }
        }

class NodeWrapper:
    """Wrapper class to make nodes comparable and hashable."""
    def __init__(self, node: Dict):
        self.node = node
        # Create a hashable representation of the node
        self.hash_key = self._create_hash_key(node)

    def _create_hash_key(self, node: Dict) -> str:
        """Create a unique string representation of the node."""
        try:
            key_parts = [
                str(node.get('type', '')),
                str(node.get('tag', '')),
                str(sorted(node.get('attrs', {}).items()) if node.get('attrs') else ''),
                str(node.get('content', '')) if node.get('type') == 'text' else ''
            ]
            return '|'.join(key_parts)
        except Exception as e:
            logger.error(f"Error creating hash key: {str(e)}", exc_info=True)
            return str(id(node))  # Fallback to object id

    def __eq__(self, other):
        if not isinstance(other, NodeWrapper):
            return False
        return self.hash_key == other.hash_key

    def __hash__(self):
        return hash(self.hash_key)

class StructureComparator:
    def __init__(self, attribute_ignore_list=None):
        self.jsx_to_html_tags = {
            'div': 'div',
            'span': 'span',
            'p': 'p',
            'a': 'a',
            'button': 'button',
            'input': 'input',
            'form': 'form',
            'img': 'img',
            'ul': 'ul',
            'ol': 'ol',
            'li': 'li',
            'h1': 'h1',
            'h2': 'h2',
            'h3': 'h3',
            'h4': 'h4',
            'h5': 'h5',
            'h6': 'h6'
        }
        
        # Add attribute name mappings
        self.jsx_to_html_attrs = {
            'className': 'class',
            'htmlFor': 'for',
            'onClick': 'onclick',
            'onChange': 'onchange',
            'onSubmit': 'onsubmit',
            'onKeyDown': 'onkeydown',
            'onKeyUp': 'onkeyup',
            'onFocus': 'onfocus',
            'onBlur': 'onblur'
        }
        
        # Add style property mappings
        self.style_property_mappings = {
            'backgroundColor': 'background-color',
            'fontSize': 'font-size',
            'fontWeight': 'font-weight',
            'marginLeft': 'margin-left',
            'marginRight': 'margin-right',
            'marginTop': 'margin-top',
            'marginBottom': 'margin-bottom',
            'paddingLeft': 'padding-left',
            'paddingRight': 'padding-right',
            'paddingTop': 'padding-top',
            'paddingBottom': 'padding-bottom'
        }
        self.attribute_ignore_list = attribute_ignore_list or []

    def _should_ignore_attr(self, attr_name):
        for pattern in self.attribute_ignore_list:
            if pattern.endswith('*'):
                if attr_name.startswith(pattern[:-1]):
                    return True
            elif attr_name == pattern:
                return True
        return False

    def normalize_jsx_node(self, node: Dict) -> Dict:
        """Convert JSX AST node to a normalized format."""
        if node.get('type') == 'jsx_element':
            return {
                'tag': node.get('openingElement', {}).get('name', {}).get('name', ''),
                'attrs': self._extract_jsx_attrs(node.get('openingElement', {}).get('attributes', [])),
                'children': [
                    self.normalize_jsx_node(child)
                    for child in node.get('children', [])
                    if self._is_valid_jsx_node(child)
                ]
            }
        elif node.get('type') == 'jsx_text':
            return {
                'type': 'text',
                'content': node.get('value', '').strip()
            }
        return {}

    def _extract_jsx_attrs(self, attrs: List[Dict]) -> Dict:
        """Extract and normalize JSX attributes."""
        result = {}
        for attr in attrs:
            if attr.get('type') == 'jsx_attribute':
                name = attr.get('name', {}).get('name', '')
                value = self._get_jsx_attr_value(attr.get('value', {}))
                if name and value:
                    # Convert JSX attribute names to HTML
                    html_name = self.jsx_to_html_attrs.get(name, name.lower())
                    result[html_name] = value
                    
                    # Handle style objects specially
                    if name == 'style' and isinstance(value, dict):
                        result[html_name] = self._normalize_style_object(value)
        return result

    def _normalize_style_object(self, style_obj: Dict) -> str:
        """Convert JSX style object to CSS string."""
        normalized = {}
        for key, value in style_obj.items():
            # Convert camelCase to kebab-case
            css_key = self.style_property_mappings.get(key) or re.sub(
                r'[A-Z]',
                lambda m: f'-{m.group(0).lower()}',
                key
            )
            normalized[css_key] = value
        
        return '; '.join(f'{k}: {v}' for k, v in sorted(normalized.items()))

    def _get_jsx_attr_value(self, value: Dict) -> str:
        """Extract value from JSX attribute."""
        if value.get('type') == 'string_literal':
            return value.get('value', '')
        elif value.get('type') == 'jsx_expression':
            expr = value.get('expression', {})
            if expr.get('type') == 'object_expression':
                # Handle style objects
                return self._extract_style_object(expr)
            # For other expressions, indicate it's dynamic
            return '[dynamic]'
        return ''

    def _extract_style_object(self, obj_expr: Dict) -> Dict:
        """Extract style properties from JSX object expression."""
        style_obj = {}
        for prop in obj_expr.get('properties', []):
            if prop.get('type') == 'object_property':
                key = prop.get('key', {}).get('name', '')
                value = prop.get('value', {}).get('value', '')
                if key and value:
                    style_obj[key] = value
        return style_obj

    def _values_match(self, html_value: Any, jsx_value: Any) -> bool:
        """Compare attribute values with normalization."""
        try:
            logger.debug(f"Comparing values - HTML: {type(html_value)}, {html_value} | JSX: {type(jsx_value)}, {jsx_value}")

            # Handle class names
            if isinstance(html_value, (list, str)) and isinstance(jsx_value, (list, str)):
                # Convert both to sets of strings for comparison
                html_classes = set(html_value if isinstance(html_value, list) 
                                 else html_value.split())
                jsx_classes = set(jsx_value if isinstance(jsx_value, list)
                                else jsx_value.split())
                return html_classes == jsx_classes
            
            # Handle JSX classes that might come as list
            if isinstance(jsx_value, list):
                jsx_classes = set(str(x) for x in jsx_value)
                if isinstance(html_value, str):
                    html_classes = set(html_value.split())
                elif isinstance(html_value, list):
                    html_classes = set(str(x) for x in html_value)
                else:
                    html_classes = {str(html_value)}
                return html_classes == jsx_classes
            
            # Handle style attributes
            if isinstance(html_value, dict) and isinstance(jsx_value, str):
                html_styles = self._parse_style_string(html_value)
                jsx_styles = self._parse_style_string(jsx_value)
                return html_styles == jsx_styles
            
            # Default string comparison
            return str(html_value).strip() == str(jsx_value).strip()

        except Exception as e:
            logger.error(f"Error comparing values: {str(e)}", exc_info=True)
            return False

    def _parse_style_string(self, style: Union[str, Dict]) -> Dict:
        """Parse CSS style string or dict into normalized dictionary."""
        try:
            logger.debug(f"Parsing style - Type: {type(style)}, Value: {style}")

            if isinstance(style, dict):
                return {k.strip(): v.strip() for k, v in style.items()}
            
            if not isinstance(style, str):
                return {}
            
            result = {}
            for declaration in style.split(';'):
                if ':' in declaration:
                    prop, value = declaration.split(':', 1)
                    result[prop.strip()] = value.strip()
            return result

        except Exception as e:
            logger.error(f"Error parsing style: {str(e)}", exc_info=True)
            return {}

    def _compare_attributes(self, html_attrs: Dict, jsx_attrs: Dict):
        """Perform detailed attribute comparison with ignore list and similarity."""
        matching = {}
        different = {}
        missing = {}
        extra = {}
        total = 0
        match_count = 0
        differing_list = []

        # Filter attributes by ignore list
        html_attrs_f = {k: v for k, v in html_attrs.items() if not self._should_ignore_attr(k)}
        jsx_attrs_f = {k: v for k, v in jsx_attrs.items() if not self._should_ignore_attr(k)}

        all_keys = set(html_attrs_f.keys()) | set(jsx_attrs_f.keys())
        for name in all_keys:
            total += 1
            html_value = html_attrs_f.get(name)
            jsx_value = jsx_attrs_f.get(name)
            if html_value is not None and jsx_value is not None:
                if self._values_match(html_value, jsx_value):
                    matching[name] = html_value
                    match_count += 1
                else:
                    different[name] = (html_value, jsx_value)
                    differing_list.append({'attribute': name, 'html': html_value, 'jsx': jsx_value})
            elif html_value is not None:
                missing[name] = html_value
                differing_list.append({'attribute': name, 'html': html_value, 'jsx': None})
            elif jsx_value is not None:
                extra[name] = jsx_value
                differing_list.append({'attribute': name, 'html': None, 'jsx': jsx_value})

        attr_similarity = match_count / total if total > 0 else 1.0
        return AttributeComparison(
            matching=matching,
            different=different,
            missing=missing,
            extra=extra
        ), differing_list, attr_similarity

    def _fuzzy_text_similarity(self, a: str, b: str) -> float:
        """Return a similarity score between 0 and 1 for two strings."""
        return difflib.SequenceMatcher(None, a, b).ratio()

    def _compare_nodes(self, html_node: Dict, jsx_node: Dict,
                      element_comparisons: List, attr_details: Dict) -> None:
        try:
            # Handle text nodes
            if html_node.get('type') == 'text' and jsx_node.get('type') == 'text':
                html_text = html_node.get('content', '').strip()
                jsx_text = jsx_node.get('content', '').strip()
                text_similarity = self._fuzzy_text_similarity(html_text, jsx_text)
                if text_similarity == 1.0:
                    element_comparisons.append({'type': 'match', 'html': html_node, 'jsx': jsx_node, 'text_similarity': text_similarity})
                else:
                    element_comparisons.append({'type': 'different', 'html': html_node, 'jsx': jsx_node, 'attribute_similarity': 1.0, 'text_similarity': text_similarity})
                return

            # Skip script content comparison but count as matching if tags match
            if html_node.get('tag') == 'script' and jsx_node.get('tag') == 'script':
                element_comparisons.append({'type': 'match', 'html': html_node, 'jsx': jsx_node, 'attribute_similarity': 1.0, 'text_similarity': 1.0})
                return

            html_tag = html_node.get('tag', '').lower()
            jsx_tag = jsx_node.get('tag', '').lower()

            if html_tag == jsx_tag:
                attrs_match, attr_diff_list, attr_similarity = self._compare_attributes(
                    html_node.get('attrs', {}),
                    jsx_node.get('attrs', {})
                )
                attr_details[html_tag] = attrs_match

                html_children = html_node.get('children', [])
                jsx_children = jsx_node.get('children', [])
                html_text = self._get_single_text_content(html_children)
                jsx_text = self._get_single_text_content(jsx_children)
                text_similarity = None
                if html_text is not None and jsx_text is not None:
                    text_similarity = self._fuzzy_text_similarity(html_text, jsx_text)

                if attr_similarity == 1.0 and (text_similarity is None or text_similarity == 1.0):
                    element_comparisons.append({'type': 'match', 'html': html_node, 'jsx': jsx_node, 'attribute_similarity': attr_similarity, 'text_similarity': text_similarity})
                else:
                    element_comparisons.append({
                        'type': 'different',
                        'html': html_node,
                        'jsx': jsx_node,
                        'attribute_similarity': attr_similarity,
                        'text_similarity': text_similarity,
                        'differing_attributes': attr_diff_list,
                        'html_text': html_text,
                        'jsx_text': jsx_text
                    })
                if html_text is None or jsx_text is None:
                    self._compare_children(
                        html_children,
                        jsx_children,
                        element_comparisons,
                        attr_details
                    )
            else:
                element_comparisons.append({'type': 'different', 'html': html_node, 'jsx': jsx_node, 'attribute_similarity': 0.0, 'text_similarity': 0.0, 'tag_mismatch': True})
        except Exception as e:
            logger.error(f"Error comparing nodes: {str(e)}", exc_info=True)
            raise

    def _get_single_text_content(self, children: list) -> str:
        """If children is a single text node, return its content, else None."""
        if len(children) == 1 and children[0].get('type') == 'text':
            return children[0].get('content', '').strip()
        return None

    def _compare_children(self, html_children: List, jsx_children: List,
                         element_comparisons: List, attr_details: Dict) -> None:
        try:
            wrapped_html = [NodeWrapper(node) for node in html_children]
            wrapped_jsx = [NodeWrapper(node) for node in jsx_children]
            matcher = difflib.SequenceMatcher(None, wrapped_html, wrapped_jsx)
            matched_html_indices = set()
            matched_jsx_indices = set()
            for i, j, n in matcher.get_matching_blocks():
                if n == 0:
                    continue
                matched_html_indices.update(range(i, i + n))
                matched_jsx_indices.update(range(j, j + n))
                for offset in range(n):
                    self._compare_nodes(
                        html_children[i + offset],
                        jsx_children[j + offset],
                        element_comparisons,
                        attr_details
                    )
            for i in range(len(html_children)):
                if i not in matched_html_indices:
                    element_comparisons.append({'type': 'missing', 'html': html_children[i], 'jsx': None})
            for j in range(len(jsx_children)):
                if j not in matched_jsx_indices:
                    element_comparisons.append({'type': 'extra', 'html': None, 'jsx': jsx_children[j]})
        except Exception as e:
            logger.error(f"Error comparing children: {str(e)}", exc_info=True)
            raise

    def compare_structures(self, html_tree: Dict, jsx_tree: Dict) -> ComparisonResult:
        try:
            element_comparisons = []
            attr_details = {}
            if html_tree and jsx_tree:
                self._compare_nodes(html_tree, jsx_tree, element_comparisons, attr_details)
            else:
                if html_tree:
                    element_comparisons.append({'type': 'missing', 'html': html_tree, 'jsx': None})
                if jsx_tree:
                    element_comparisons.append({'type': 'extra', 'html': None, 'jsx': jsx_tree})
            # Per-element score aggregation
            element_scores = []
            matching = []
            different = []
            missing = []
            extra = []
            for comp in element_comparisons:
                if comp['type'] == 'match':
                    element_scores.append(1.0)
                    matching.append((comp['html'], comp['jsx']))
                elif comp['type'] == 'different':
                    attr_score = comp.get('attribute_similarity', 0)
                    text_score = comp.get('text_similarity', 0)
                    # If text_score is None, treat as 1.0 (for non-text elements)
                    if text_score is None:
                        text_score = 1.0
                    partial_score = 0.5 * attr_score + 0.5 * text_score
                    element_scores.append(min(partial_score, 1.0))
                    different.append((comp['html'], comp['jsx']))
                elif comp['type'] == 'missing':
                    element_scores.append(0.0)
                    missing.append(comp['html'])
                elif comp['type'] == 'extra':
                    element_scores.append(0.0)
                    extra.append(comp['jsx'])
            similarity_score = sum(element_scores) / len(element_scores) if element_scores else 0.0
            return ComparisonResult(
                similarity_score=similarity_score,
                matching_elements=matching,
                different_elements=different,
                missing_elements=missing,
                extra_elements=extra,
                attribute_details=attr_details
            )
        except Exception as e:
            logger.error(f"Error during comparison: {str(e)}", exc_info=True)
            raise

    def generate_diff_report(self, result: ComparisonResult) -> Dict:
        """Generate a detailed diff report from comparison results."""
        try:
            return result.to_dict()
        except Exception as e:
            logger.error(f"Error generating diff report: {str(e)}", exc_info=True)
            # Return a valid empty result structure if there's an error
            return {
                'similarity_scores': {
                    'overall': 0.0,
                    'html': 0.0,
                    'jsx': 0.0,
                },
                'summary': {
                    'html': {
                        'matching_elements': 0,
                        'different_elements': 0,
                        'missing_elements': 0,
                        'extra_elements': 0,
                        'total_elements': 0
                    },
                    'jsx': {
                        'matching_elements': 0,
                        'different_elements': 0,
                        'missing_elements': 0,
                        'extra_elements': 0,
                        'total_elements': 0
                    }
                },
                'details': {
                    'attribute_details': {}
                }
            } 