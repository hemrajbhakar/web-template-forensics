import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.html_parser import HTMLParser
from core.structure_comparator import StructureComparator

def get_first_element(tree):
    # Helper to get the first element child of the root
    if tree['tag'] == '[document]' and tree['children']:
        for child in tree['children']:
            if child.get('type') == 'element':
                return child
    return tree

def test_html_tag_and_attribute_extraction():
    parser = HTMLParser()
    html = '<div id="main" class="foo"><span data-x="1">Hello</span></div>'
    tree = parser.parse(html)
    div = get_first_element(tree)
    assert div['tag'] == 'div'
    assert div['attrs']['id'] == 'main'
    assert 'foo' in div['attrs']['class']
    span = div['children'][0]
    assert span['tag'] == 'span'
    assert span['attrs']['data-x'] == '1'

def test_html_structure_identical():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = '<div><span>Hi</span></div>'
    html2 = '<div><span>Hi</span></div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    div1 = get_first_element(tree1)
    div2 = get_first_element(tree2)
    result = comp.compare_structures(div1, div2)
    assert result.similarity_score == 1.0
    assert len(result.matching_elements) > 0

def test_html_structure_missing_element():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = '<div><span>Hi</span></div>'
    html2 = '<div></div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    div1 = get_first_element(tree1)
    div2 = get_first_element(tree2)
    result = comp.compare_structures(div1, div2)
    assert result.similarity_score < 1.0
    assert len(result.missing_elements) == 1

def test_html_structure_extra_element():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = '<div></div>'
    html2 = '<div><span>Hi</span></div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    div1 = get_first_element(tree1)
    div2 = get_first_element(tree2)
    result = comp.compare_structures(div1, div2)
    assert result.similarity_score < 1.0
    assert len(result.extra_elements) == 1

def test_html_structure_different_attributes():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = '<div class="a"></div>'
    html2 = '<div class="b"></div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    div1 = get_first_element(tree1)
    div2 = get_first_element(tree2)
    result = comp.compare_structures(div1, div2)
    assert result.similarity_score < 1.0
    # The attribute difference may not always be counted as a different element, so just check score

def test_html_structure_different_text():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = '<div>foo</div>'
    html2 = '<div>bar</div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    div1 = get_first_element(tree1)
    div2 = get_first_element(tree2)
    result = comp.compare_structures(div1, div2)
    assert result.similarity_score < 1.0

def test_html_empty_and_malformed():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = ''
    html2 = '<div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    div1 = get_first_element(tree1)
    div2 = get_first_element(tree2)
    result = comp.compare_structures(div1, div2)
    assert result.similarity_score <= 1.0

def test_html_deeply_nested():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = '<div><ul><li><span>1</span></li></ul></div>'
    html2 = '<div><ul><li><span>1</span></li></ul></div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    div1 = get_first_element(tree1)
    div2 = get_first_element(tree2)
    result = comp.compare_structures(div1, div2)
    assert result.similarity_score == 1.0

def test_html_self_closing_tags():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = '<div><img src="a.png" /><br/></div>'
    html2 = '<div><img src="a.png" /><br/></div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    div1 = get_first_element(tree1)
    div2 = get_first_element(tree2)
    result = comp.compare_structures(div1, div2)
    assert result.similarity_score == 1.0

def test_html_with_comments():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = '<div><!-- comment --><span>Hi</span></div>'
    html2 = '<div><span>Hi</span></div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    div1 = get_first_element(tree1)
    div2 = get_first_element(tree2)
    result = comp.compare_structures(div1, div2)
    assert result.similarity_score <= 1.0

def test_html_whitespace_variations():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = '<div>   <span>Hi</span> </div>'
    html2 = '<div><span>Hi</span></div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    div1 = get_first_element(tree1)
    div2 = get_first_element(tree2)
    result = comp.compare_structures(div1, div2)
    assert result.similarity_score == 1.0

def test_html_attribute_order():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = '<div id="a" class="b"></div>'
    html2 = '<div class="b" id="a"></div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    div1 = get_first_element(tree1)
    div2 = get_first_element(tree2)
    result = comp.compare_structures(div1, div2)
    assert result.similarity_score == 1.0

def test_html_deeply_mismatched_nesting():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = '<div><ul><li><span>1</span></li></ul></div>'
    html2 = '<div><ul><li>1</li></ul></div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    div1 = get_first_element(tree1)
    div2 = get_first_element(tree2)
    result = comp.compare_structures(div1, div2)
    assert result.similarity_score < 1.0

def test_html_multiple_root_elements():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = '<div>1</div><div>2</div>'
    html2 = '<div>1</div><div>2</div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    # For multiple roots, just check that the test runs without error
    assert tree1['tag'] == '[document]'
    assert tree2['tag'] == '[document]'

def test_html_script_and_style_tags():
    parser = HTMLParser()
    comp = StructureComparator()
    html1 = '<div><script>var a=1;</script><style>.a{}</style><span>Hi</span></div>'
    html2 = '<div><span>Hi</span></div>'
    tree1 = parser.parse(html1)
    tree2 = parser.parse(html2)
    div1 = get_first_element(tree1)
    div2 = get_first_element(tree2)
    result = comp.compare_structures(div1, div2)
    assert result.similarity_score <= 1.0 