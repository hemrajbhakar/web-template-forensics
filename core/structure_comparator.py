"""
Structure Comparator Module
Compares HTML and JSX structures to find similarities and differences.
"""

from typing import Dict, List, Tuple, Set, Optional, Union, Any
import difflib
from dataclasses import dataclass, field
import logging
import json

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
                'attribute_details': self.attribute_details
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
    def __init__(self):
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

    def _compare_attributes(self, html_attrs: Dict, jsx_attrs: Dict) -> AttributeComparison:
        """Perform detailed attribute comparison."""
        matching = {}
        different = {}
        missing = {}
        extra = {}
        
        # Compare common attributes
        for name, html_value in html_attrs.items():
            if name in jsx_attrs:
                jsx_value = jsx_attrs[name]
                if self._values_match(html_value, jsx_value):
                    matching[name] = html_value
                else:
                    different[name] = (html_value, jsx_value)
            else:
                missing[name] = html_value
        
        # Find extra JSX attributes
        for name, jsx_value in jsx_attrs.items():
            if name not in html_attrs:
                extra[name] = jsx_value
        
        return AttributeComparison(
            matching=matching,
            different=different,
            missing=missing,
            extra=extra
        )

    def _is_valid_jsx_node(self, node: Dict) -> bool:
        """Check if JSX node should be included in comparison."""
        if node.get('type') == 'jsx_text':
            return bool(node.get('value', '').strip())
        return node.get('type') == 'jsx_element'

    def _compare_nodes(self, html_node: Dict, jsx_node: Dict,
                      matching: List, different: List, missing: List, extra: List,
                      attr_details: Dict) -> None:
        """Compare individual nodes and their children."""
        try:
            # Handle text nodes
            if html_node.get('type') == 'text' and jsx_node.get('type') == 'text':
                logger.debug(f"Comparing text nodes")
                if html_node.get('content', '').strip() == jsx_node.get('content', '').strip():
                    logger.debug("Text nodes match")
                    matching.append((html_node, jsx_node))
                else:
                    logger.debug("Text nodes differ")
                    different.append((html_node, jsx_node))
                return

            # Skip script content comparison but count as matching if tags match
            if html_node.get('tag') == 'script' and jsx_node.get('tag') == 'script':
                logger.debug("Matching script tags, skipping content comparison")
                matching.append((html_node, jsx_node))
                return

            logger.debug(f"Comparing nodes - HTML: {html_node.get('tag', 'unknown')} JSX: {jsx_node.get('tag', 'unknown')}")

            html_tag = html_node.get('tag', '').lower()
            jsx_tag = jsx_node.get('tag', '').lower()

            if html_tag == jsx_tag:
                attrs_match = self._compare_attributes(
                    html_node.get('attrs', {}),
                    jsx_node.get('attrs', {})
                )
                attr_details[html_tag] = attrs_match

                if attrs_match.different or attrs_match.missing or attrs_match.extra:
                    logger.debug(f"Attributes differ for tag {html_tag}")
                    different.append((html_node, jsx_node))
                else:
                    logger.debug(f"Nodes match for tag {html_tag}")
                    matching.append((html_node, jsx_node))

                self._compare_children(
                    html_node.get('children', []),
                    jsx_node.get('children', []),
                    matching, different, missing, extra,
                    attr_details
                )
            else:
                logger.debug(f"Tags differ: HTML={html_tag}, JSX={jsx_tag}")
                different.append((html_node, jsx_node))

        except Exception as e:
            logger.error(f"Error comparing nodes: {str(e)}", exc_info=True)
            raise

    def _compare_children(self, html_children: List, jsx_children: List,
                         matching: List, different: List, missing: List, extra: List,
                         attr_details: Dict) -> None:
        """Compare child nodes using wrapped nodes for comparison."""
        try:
            logger.debug(f"Comparing children - HTML count: {len(html_children)}, JSX count: {len(jsx_children)}")

            # Wrap nodes for comparison
            wrapped_html = [NodeWrapper(node) for node in html_children]
            wrapped_jsx = [NodeWrapper(node) for node in jsx_children]

            # Create sequence matcher with wrapped nodes
            matcher = difflib.SequenceMatcher(None, wrapped_html, wrapped_jsx)

            # Process matching blocks
            # get_matching_blocks() returns tuples of (i, j, n) where:
            # i is the start index in sequence 1
            # j is the start index in sequence 2
            # n is the length of the match
            matched_html_indices = set()
            matched_jsx_indices = set()

            for i, j, n in matcher.get_matching_blocks():
                if n == 0:  # Skip zero-length matches
                    continue
                    
                matched_html_indices.update(range(i, i + n))
                matched_jsx_indices.update(range(j, j + n))
                
                # Compare matched children
                for offset in range(n):
                    self._compare_nodes(
                        html_children[i + offset],
                        jsx_children[j + offset],
                        matching, different, missing, extra,
                        attr_details
                    )

            # Add unmatched nodes to missing and extra lists
            missing.extend(html_children[i] for i in range(len(html_children))
                         if i not in matched_html_indices)
            extra.extend(jsx_children[j] for j in range(len(jsx_children))
                        if j not in matched_jsx_indices)

        except Exception as e:
            logger.error(f"Error comparing children: {str(e)}", exc_info=True)
            raise

    def compare_structures(self, html_tree: Dict, jsx_tree: Dict) -> ComparisonResult:
        """Compare HTML and JSX structures."""
        try:
            logger.info("Starting structure comparison")
            logger.debug(f"HTML tree: {json.dumps(html_tree, indent=2)}")
            logger.debug(f"JSX tree: {json.dumps(jsx_tree, indent=2)}")

            matching = []
            different = []
            missing = []
            extra = []
            attr_details = {}

            if html_tree and jsx_tree:
                self._compare_nodes(html_tree, jsx_tree, matching, different, missing, extra, attr_details)
            else:
                logger.warning("One or both trees are empty")
                if html_tree:
                    missing.append(html_tree)
                if jsx_tree:
                    extra.append(jsx_tree)

            total_elements = len(matching) + len(different) + len(missing) + len(extra)
            similarity_score = len(matching) / total_elements if total_elements > 0 else 0.0

            logger.info(f"Comparison complete. Similarity score: {similarity_score}")
            logger.debug(f"Matching elements: {len(matching)}")
            logger.debug(f"Different elements: {len(different)}")
            logger.debug(f"Missing elements: {len(missing)}")
            logger.debug(f"Extra elements: {len(extra)}")

            # Create summary data
            summary = {
                'matching_elements': len(matching),
                'different_elements': len(different),
                'missing_elements': len(missing),
                'extra_elements': len(extra),
                'total_elements': total_elements,
                'similarity_score': similarity_score
            }

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