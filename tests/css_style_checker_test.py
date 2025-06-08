import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.css_style_checker import CSSStyleChecker

def test_css_selector_and_property_extraction():
    checker = CSSStyleChecker()
    css = ".foo { color: #fff; margin: 0; } .bar { padding: 1rem; }"
    rules, *_ = checker.parse_css(css)
    assert '.foo' in rules
    assert '.bar' in rules
    assert rules['.foo']['color'][0] == '#fff'
    assert rules['.bar']['padding'][0] == '1rem'

def test_css_identical():
    checker = CSSStyleChecker()
    css1 = ".foo { color: #fff; }"
    css2 = ".foo { color: #ffffff; }"
    result = checker.compare_css(css1, css2)
    assert result['css_similarity'] == 1.0

def test_css_missing_selector():
    checker = CSSStyleChecker()
    css1 = ".foo { color: #fff; } .bar { margin: 0; }"
    css2 = ".foo { color: #fff; }"
    result = checker.compare_css(css1, css2)
    assert result['css_similarity'] < 1.0
    assert result['missing_selectors'] == 1

def test_css_extra_selector():
    checker = CSSStyleChecker()
    css1 = ".foo { color: #fff; }"
    css2 = ".foo { color: #fff; } .bar { margin: 0; }"
    result = checker.compare_css(css1, css2)
    assert result['css_similarity'] < 1.0
    assert result['extra_selectors'] == 1

def test_css_partial_property_match():
    checker = CSSStyleChecker()
    css1 = ".foo { color: #fff; margin: 0; }"
    css2 = ".foo { color: #fff; padding: 1rem; }"
    result = checker.compare_css(css1, css2)
    assert 0 < result['css_similarity'] < 1.0

def test_css_empty_and_malformed():
    checker = CSSStyleChecker()
    css1 = ""
    css2 = ".foo { }"
    result = checker.compare_css(css1, css2)
    assert result['css_similarity'] <= 1.0

def test_css_media_queries():
    checker = CSSStyleChecker()
    css1 = "@media (min-width: 600px) { .foo { color: red; } }"
    css2 = "@media (min-width: 600px) { .foo { color: red; } }"
    result = checker.compare_css(css1, css2)
    assert result['css_similarity'] == 1.0
    assert 'media_queries' in result

def test_css_with_comments():
    checker = CSSStyleChecker()
    css1 = ".foo { color: #fff; } /* comment */"
    css2 = ".foo { color: #fff; }"
    result = checker.compare_css(css1, css2)
    assert result['css_similarity'] == 1.0

def test_css_whitespace_variations():
    checker = CSSStyleChecker()
    css1 = ".foo{color:#fff;}"
    css2 = ".foo { color: #fff; }"
    result = checker.compare_css(css1, css2)
    assert result['css_similarity'] == 1.0

def test_css_selector_order():
    checker = CSSStyleChecker()
    css1 = ".a {x:1;} .b {y:2;}"
    css2 = ".b {y:2;} .a {x:1;}"
    result = checker.compare_css(css1, css2)
    assert result['css_similarity'] == 1.0

def test_css_empty_selectors():
    checker = CSSStyleChecker()
    css1 = ".foo {}"
    css2 = ".foo {}"
    result = checker.compare_css(css1, css2)
    assert result['css_similarity'] == 1.0

def test_css_duplicate_selectors():
    checker = CSSStyleChecker()
    css1 = ".foo { color: #fff; } .foo { margin: 0; }"
    css2 = ".foo { color: #fff; margin: 0; }"
    result = checker.compare_css(css1, css2)
    assert result['css_similarity'] == 1.0

def test_css_at_rules():
    checker = CSSStyleChecker()
    css1 = "@import url('a.css'); .foo { color: #fff; }"
    css2 = ".foo { color: #fff; }"
    result = checker.compare_css(css1, css2)
    assert result['css_similarity'] == 1.0

def test_css_invalid():
    checker = CSSStyleChecker()
    css1 = ".foo { color: }"
    css2 = ".foo { color: #fff; }"
    result = checker.compare_css(css1, css2)
    assert result['css_similarity'] <= 1.0 