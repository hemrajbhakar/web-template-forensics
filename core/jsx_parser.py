"""
JSX Parser Module
A simple parser for analyzing React/JSX components.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import re

class JSXParser:
    def __init__(self):
        self.source_code = ""
    
    def parse_jsx_file(self, file_path: Union[str, Path]) -> Dict:
        """Parse JSX/TSX file and create component structure."""
        path = Path(file_path)
        
        # Read the source file
        with open(path, 'r', encoding='utf-8') as f:
            self.source_code = f.read()
        
        # Find the first JSX element
        jsx_match = re.search(r'<(\w+)([^>]*)>(.*?)</\1>|<(\w+)([^>]*)/>', self.source_code, re.DOTALL)
        if not jsx_match:
            return {"error": "No JSX element found"}
        
        # Parse the matched JSX
        if jsx_match.group(4):  # Self-closing tag
            tag_name = jsx_match.group(4)
            props = self._parse_props(jsx_match.group(5))
            return {
                "tag": tag_name,
                "props": props,
                "children": []
            }
        else:  # Regular tag
            tag_name = jsx_match.group(1)
            props = self._parse_props(jsx_match.group(2))
            children = self._parse_children(jsx_match.group(3))
            return {
                "tag": tag_name,
                "props": props,
                "children": children
            }
    
    def _parse_props(self, props_str: str) -> Dict[str, Any]:
        """Parse JSX props string into a dictionary."""
        props = {}
        
        # Match props with values
        for match in re.finditer(r'(\w+)=(?:"([^"]*)"|{([^}]*)})', props_str):
            name = match.group(1)
            value = match.group(2) if match.group(2) else match.group(3)
            props[name] = value
        
        # Match spread props
        for match in re.finditer(r'{\.\.\.([^}]*)}', props_str):
            props['__spread'] = match.group(1)
        
        return props
    
    def _parse_children(self, children_str: str) -> List[Dict]:
        """Parse JSX children string into a list of nodes."""
        children = []
        
        # Find all child JSX elements
        pos = 0
        while pos < len(children_str):
            # Skip whitespace
            while pos < len(children_str) and children_str[pos].isspace():
                pos += 1
            
            if pos >= len(children_str):
                break
            
            # Check for JSX expression
            if children_str[pos] == '{':
                end = children_str.find('}', pos)
                if end != -1:
                    expr = children_str[pos+1:end].strip()
                    if expr:
                        children.append({
                            "type": "expression",
                            "content": expr
                        })
                    pos = end + 1
                    continue
            
            # Check for JSX element
            if children_str[pos] == '<':
                # Find matching closing tag
                tag_match = re.match(r'<(\w+)([^>]*)>(.*?)</\1>|<(\w+)([^>]*)/>', children_str[pos:], re.DOTALL)
                if tag_match:
                    if tag_match.group(4):  # Self-closing tag
                        tag_name = tag_match.group(4)
                        props = self._parse_props(tag_match.group(5))
                        children.append({
                            "tag": tag_name,
                            "props": props,
                            "children": []
                        })
                        pos += len(tag_match.group(0))
                    else:  # Regular tag
                        tag_name = tag_match.group(1)
                        props = self._parse_props(tag_match.group(2))
                        inner_children = self._parse_children(tag_match.group(3))
                        children.append({
                            "tag": tag_name,
                            "props": props,
                            "children": inner_children
                        })
                        pos += len(tag_match.group(0))
                    continue
            
            # Check for text content
            text_end = pos
            while text_end < len(children_str):
                if children_str[text_end] in '{<':
                    break
                text_end += 1
            
            text = children_str[pos:text_end].strip()
            if text:
                children.append({
                    "type": "text",
                    "content": text
                })
            pos = text_end
        
        return children 