"""
HTML Parser Module
Parses HTML content into a structured format for comparison.
"""

from bs4 import BeautifulSoup
from typing import Dict, List, Union, Optional
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class HTMLParser:
    """Parser for HTML content."""
    
    def __init__(self):
        """Initialize the HTML parser."""
        self.void_elements = {
            'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
            'link', 'meta', 'param', 'source', 'track', 'wbr'
        }

    def parse_file(self, file_path: Union[str, Path]) -> Dict:
        """Parse HTML file and return structured format."""
        try:
            logger.info(f"Starting to parse file: {file_path}")
            path = Path(file_path)
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"Successfully read file, content length: {len(content)}")
                
            return self.parse(content)
            
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {str(e)}", exc_info=True)
            raise

    def parse(self, html_content: str) -> Dict:
        """Parse HTML content into a structured format."""
        try:
            logger.info("Starting HTML parsing")
            logger.debug(f"Input HTML content length: {len(html_content)}")

            # Parse HTML using BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            logger.debug("BeautifulSoup parsing complete")

            # Start with the body tag if it exists, otherwise use the root
            root = soup.body if soup.body else soup
            logger.debug(f"Using root element: {root.name}")

            # Parse the tree structure
            result = self._parse_node(root)
            logger.info("HTML parsing complete")
            return result

        except Exception as e:
            logger.error(f"Error parsing HTML: {str(e)}", exc_info=True)
            raise

    def _parse_node(self, node) -> Dict:
        """Parse a single HTML node and its children."""
        try:
            # Skip comment nodes
            if node.name is None or isinstance(node, (str, bytes)):
                text_content = str(node).strip()
                if text_content:
                    logger.debug(f"Found text node: {text_content[:50]}...")
                    return {'type': 'text', 'content': text_content}
                return None

            logger.debug(f"Parsing node: {node.name}")

            # Extract attributes
            attrs = self._parse_attributes(node)
            logger.debug(f"Node attributes: {attrs}")

            # Parse children
            children = []
            for child in node.children:
                child_node = self._parse_node(child)
                if child_node:
                    children.append(child_node)

            logger.debug(f"Node {node.name} has {len(children)} children")

            # Build node structure
            result = {
                'type': 'element',
                'tag': node.name,
                'attrs': attrs,
                'children': children
            }

            return result

        except Exception as e:
            logger.error(f"Error parsing node {getattr(node, 'name', 'unknown')}: {str(e)}", exc_info=True)
            raise

    def _parse_attributes(self, node) -> Dict:
        """Parse HTML node attributes."""
        try:
            attrs = {}
            
            # Convert BeautifulSoup attrs to dict
            for key, value in node.attrs.items():
                logger.debug(f"Processing attribute: {key}")
                
                # Handle class attribute specially
                if key == 'class':
                    attrs[key] = value if isinstance(value, list) else value.split()
                    logger.debug(f"Processed class attribute: {attrs[key]}")
                # Handle style attribute
                elif key == 'style':
                    if isinstance(value, dict):
                        attrs[key] = value
                    else:
                        style_dict = {}
                        for style in value.split(';'):
                            if ':' in style:
                                prop, val = style.split(':', 1)
                                style_dict[prop.strip()] = val.strip()
                        attrs[key] = style_dict
                    logger.debug(f"Processed style attribute: {attrs[key]}")
                # Handle other attributes
                else:
                    attrs[key] = value
                    logger.debug(f"Processed {key} attribute: {value}")

            return attrs

        except Exception as e:
            logger.error(f"Error parsing attributes: {str(e)}", exc_info=True)
            return {}