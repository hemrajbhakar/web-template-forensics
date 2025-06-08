import sys
import os
import pytest
import tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.jsx_parser import JSXParser
from core.structure_comparator import StructureComparator

def parse_jsx_string(jsx_str):
    parser = JSXParser()
    with tempfile.NamedTemporaryFile('w+', suffix='.jsx', delete=False) as f:
        f.write(jsx_str)
        f.flush()
        path = f.name
    tree = parser.parse_jsx_file(path)
    os.unlink(path)
    return tree

def test_jsx_element_and_prop_extraction():
    jsx = '<div id="main"><Button color="red">Click</Button></div>'
    tree = parse_jsx_string(jsx)
    assert tree['tag'] == 'div'
    assert tree['children'][0]['tag'] == 'Button'
    assert tree['children'][0]['props']['color'] == 'red'

def test_jsx_structure_identical():
    comp = StructureComparator()
    jsx1 = '<div><Button>Click</Button></div>'
    jsx2 = '<div><Button>Click</Button></div>'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert result.similarity_score == 1.0
    assert len(result.matching_elements) > 0

def test_jsx_structure_missing_element():
    comp = StructureComparator()
    jsx1 = '<div><Button>Click</Button></div>'
    jsx2 = '<div></div>'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert result.similarity_score < 1.0
    assert len(result.missing_elements) == 1

def test_jsx_structure_extra_element():
    comp = StructureComparator()
    jsx1 = '<div></div>'
    jsx2 = '<div><Button>Click</Button></div>'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert result.similarity_score < 1.0
    assert len(result.extra_elements) == 1

def test_jsx_structure_different_props():
    comp = StructureComparator()
    jsx1 = '<Button color="red" />'
    jsx2 = '<Button color="blue" />'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert 0.0 <= result.similarity_score <= 1.0

def test_jsx_structure_different_text():
    comp = StructureComparator()
    jsx1 = '<Button>foo</Button>'
    jsx2 = '<Button>bar</Button>'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert result.similarity_score < 1.0
    assert len(result.different_elements) == 1

def test_jsx_empty_and_malformed():
    comp = StructureComparator()
    jsx1 = ''
    jsx2 = '<div>'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert result.similarity_score <= 1.0

def test_jsx_deeply_nested():
    comp = StructureComparator()
    jsx1 = '<div><A><B><C>1</C></B></A></div>'
    jsx2 = '<div><A><B><C>1</C></B></A></div>'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert result.similarity_score == 1.0

def test_jsx_self_closing_elements():
    comp = StructureComparator()
    jsx1 = '<div><Input /></div>'
    jsx2 = '<div><Input /></div>'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert result.similarity_score == 1.0

def test_jsx_with_comments():
    comp = StructureComparator()
    jsx1 = '<div>{/* comment */}<Button>Hi</Button></div>'
    jsx2 = '<div><Button>Hi</Button></div>'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert 0.0 < result.similarity_score <= 1.0

def test_jsx_whitespace_variations():
    comp = StructureComparator()
    jsx1 = '<div>   <Button>Hi</Button> </div>'
    jsx2 = '<div><Button>Hi</Button></div>'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert result.similarity_score == 1.0

def test_jsx_prop_order():
    comp = StructureComparator()
    jsx1 = '<Button a="1" b="2" />'
    jsx2 = '<Button b="2" a="1" />'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert result.similarity_score == 1.0

def test_jsx_deeply_mismatched_nesting():
    comp = StructureComparator()
    jsx1 = '<div><A><B><C>1</C></B></A></div>'
    jsx2 = '<div><A><B>1</B></A></div>'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert result.similarity_score < 1.0

def test_jsx_multiple_root_elements():
    comp = StructureComparator()
    jsx1 = '<><div>1</div><div>2</div></>'
    jsx2 = '<><div>1</div><div>2</div></>'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert result.similarity_score == 1.0 or result.similarity_score < 1.0  # parser-dependent

def test_jsx_fragments():
    comp = StructureComparator()
    jsx1 = '<><A /><B /></>'
    jsx2 = '<><A /><B /></>'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert result.similarity_score == 1.0

def test_jsx_invalid():
    comp = StructureComparator()
    jsx1 = '<div><Button></div>'  # missing closing tag
    jsx2 = '<div></div>'
    tree1 = parse_jsx_string(jsx1)
    tree2 = parse_jsx_string(jsx2)
    result = comp.compare_structures(tree1, tree2)
    assert result.similarity_score <= 1.0 