import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.tailwind_analyzer import TailwindAnalyzer

SAMPLE_HTML = '<div class="bg-red-500 text-lg flex items-center">Hello</div>'
SAMPLE_JSX = '<div className="p-4 m-2 text-center">World</div>'

SAMPLE_CONFIG_ORIG = {
    'theme': {
        'extend': {
            'colors': {'primary': '#123456'},
            'spacing': {'72': '18rem'},
            'fontSize': {'xxl': '2rem'}
        }
    }
}
SAMPLE_CONFIG_USER = {
    'theme': {
        'extend': {
            'colors': {'primary': '#123456', 'secondary': '#654321'},
            'fontSize': {'xxl': '2rem'},
            'borderRadius': {'xl': '1rem'}
        }
    }
}

def test_extract_classes():
    analyzer = TailwindAnalyzer()
    html_classes = analyzer.extract_classes(SAMPLE_HTML)
    jsx_classes = analyzer.extract_classes(SAMPLE_JSX)
    assert 'bg-red-500' in html_classes
    assert 'flex' in html_classes
    assert 'p-4' in jsx_classes
    assert 'text-center' in jsx_classes
    assert len(html_classes) == 4
    assert len(jsx_classes) == 3

def test_extract_classes_empty():
    analyzer = TailwindAnalyzer()
    html = '<div class="">Empty</div>'
    assert analyzer.extract_classes(html) == set()
    jsx = '<div className="">Empty</div>'
    assert analyzer.extract_classes(jsx) == set()

def test_extract_classes_multiple_attrs():
    analyzer = TailwindAnalyzer()
    html = '<div class="foo bar" className="baz qux">Test</div>'
    classes = analyzer.extract_classes(html)
    assert 'foo' in classes
    assert 'bar' in classes
    assert 'baz' in classes
    assert 'qux' in classes
    assert len(classes) == 4

def test_extract_classes_whitespace():
    analyzer = TailwindAnalyzer()
    html = '<div class="  foo   bar\n   baz\tqux  ">Test</div>'
    classes = analyzer.extract_classes(html)
    assert set(classes) == {'foo', 'bar', 'baz', 'qux'}

def test_jaccard_similarity():
    analyzer = TailwindAnalyzer()
    set1 = {'a', 'b', 'c'}
    set2 = {'b', 'c', 'd'}
    sim = analyzer.jaccard_similarity(set1, set2)
    assert sim == 0.5
    sim_full = analyzer.jaccard_similarity({'a'}, {'a'})
    assert sim_full == 1.0
    sim_empty = analyzer.jaccard_similarity(set(), set())
    assert sim_empty == 1.0
    sim_one_empty = analyzer.jaccard_similarity({'a'}, set())
    assert sim_one_empty == 0.0
    sim_one_empty2 = analyzer.jaccard_similarity(set(), {'b'})
    assert sim_one_empty2 == 0.0

def test_compare_classes():
    analyzer = TailwindAnalyzer()
    result = analyzer.compare_classes(SAMPLE_HTML, SAMPLE_JSX, 'html')
    assert 'shared_classes' in result
    assert 'only_in_original' in result
    assert 'only_in_user' in result
    assert result['jaccard_similarity'] < 1.0
    # identical
    result2 = analyzer.compare_classes(SAMPLE_HTML, SAMPLE_HTML, 'html')
    assert result2['jaccard_similarity'] == 1.0
    assert set(result2['shared_classes']) == analyzer.extract_classes(SAMPLE_HTML, 'html')

def test_compare_classes_no_overlap():
    analyzer = TailwindAnalyzer()
    html1 = '<div class="foo bar">A</div>'
    html2 = '<div class="baz qux">B</div>'
    result = analyzer.compare_classes(html1, html2, 'html')
    assert result['jaccard_similarity'] == 0.0
    assert result['shared_classes'] == []
    assert set(result['only_in_original']) == {'foo', 'bar'}
    assert set(result['only_in_user']) == {'baz', 'qux'}

def test_extract_theme_extensions():
    analyzer = TailwindAnalyzer()
    orig_ext = analyzer.extract_theme_extensions(SAMPLE_CONFIG_ORIG)
    user_ext = analyzer.extract_theme_extensions(SAMPLE_CONFIG_USER)
    assert 'colors' in orig_ext
    assert 'spacing' in orig_ext
    assert 'fontSize' in orig_ext
    assert 'colors' in user_ext
    assert 'fontSize' in user_ext
    assert 'borderRadius' in user_ext

def test_extract_theme_extensions_missing_extend():
    analyzer = TailwindAnalyzer()
    config = {'theme': {}}
    ext = analyzer.extract_theme_extensions(config)
    assert ext == {}
    config2 = {}
    ext2 = analyzer.extract_theme_extensions(config2)
    assert ext2 == {}

def test_compare_configs(monkeypatch):
    analyzer = TailwindAnalyzer()
    # Monkeypatch parse_config to return our dicts
    monkeypatch.setattr(analyzer, 'parse_config', lambda path: SAMPLE_CONFIG_ORIG if 'orig' in path else SAMPLE_CONFIG_USER)
    result = analyzer.compare_configs('orig_path', 'user_path')
    assert 'shared_config_keys' in result
    assert 'only_in_original_config' in result
    assert 'only_in_user_config' in result
    assert 'colors' in result['shared_config_keys']
    assert 'spacing' in result['only_in_original_config']
    assert 'borderRadius' in result['only_in_user_config']
    assert result['key_jaccard_similarity'] > 0.0

def test_compare_configs_all_keys_match(monkeypatch):
    analyzer = TailwindAnalyzer()
    config1 = {'theme': {'extend': {'colors': {}, 'spacing': {}}}}
    config2 = {'theme': {'extend': {'colors': {}, 'spacing': {}}}}
    monkeypatch.setattr(analyzer, 'parse_config', lambda path: config1)
    result = analyzer.compare_configs('a', 'b')
    assert set(result['shared_config_keys']) == {'colors', 'spacing'}
    assert result['only_in_original_config'] == []
    assert result['only_in_user_config'] == []
    assert result['key_jaccard_similarity'] == 1.0

def test_compare_configs_no_keys_match(monkeypatch):
    analyzer = TailwindAnalyzer()
    config1 = {'theme': {'extend': {'colors': {}}}}
    config2 = {'theme': {'extend': {'spacing': {}}}}
    monkeypatch.setattr(analyzer, 'parse_config', lambda path: config1 if '1' in path else config2)
    result = analyzer.compare_configs('1', '2')
    assert result['shared_config_keys'] == []
    assert set(result['only_in_original_config']) == {'colors'}
    assert set(result['only_in_user_config']) == {'spacing'}
    assert result['key_jaccard_similarity'] == 0.0

def test_compare_configs_extra_keys(monkeypatch):
    analyzer = TailwindAnalyzer()
    config1 = {'theme': {'extend': {'colors': {}, 'spacing': {}, 'fontSize': {}}}}
    config2 = {'theme': {'extend': {'colors': {}}}}
    monkeypatch.setattr(analyzer, 'parse_config', lambda path: config1 if '1' in path else config2)
    result = analyzer.compare_configs('1', '2')
    assert set(result['shared_config_keys']) == {'colors'}
    assert set(result['only_in_original_config']) == {'spacing', 'fontSize'}
    assert result['only_in_user_config'] == []
    assert result['key_jaccard_similarity'] == 1/3

def test_compare_configs_error(monkeypatch):
    analyzer = TailwindAnalyzer()
    monkeypatch.setattr(analyzer, 'parse_config', lambda path: {'error': 'fail'})
    result = analyzer.compare_configs('a', 'b')
    assert result['original_config'] == {}
    assert result['user_config'] == {}
    assert result['shared_config_keys'] == []
    assert result['only_in_original_config'] == []
    assert result['only_in_user_config'] == []
    assert result['key_jaccard_similarity'] == 1.0

def test_full_report_mock():
    # Simulate a full report structure
    analyzer = TailwindAnalyzer()
    class_result = analyzer.compare_classes(SAMPLE_HTML, SAMPLE_HTML, 'html')
    config_result = {
        'shared_config_keys': ['colors', 'fontSize'],
        'only_in_original_config': ['spacing'],
        'only_in_user_config': ['borderRadius'],
        'key_jaccard_similarity': 0.5
    }
    report = {
        'class_similarity': class_result['jaccard_similarity'],
        'config_similarity': config_result['key_jaccard_similarity'],
        'shared_classes': class_result['shared_classes'],
        'only_in_original': class_result['only_in_original'],
        'only_in_user': class_result['only_in_user'],
        'shared_config_keys': config_result['shared_config_keys'],
        'only_in_original_config': config_result['only_in_original_config'],
        'only_in_user_config': config_result['only_in_user_config'],
    }
    assert report['class_similarity'] == 1.0
    assert 'bg-red-500' in report['shared_classes']
    assert report['config_similarity'] == 0.5
    assert 'spacing' in report['only_in_original_config']
    assert 'borderRadius' in report['only_in_user_config'] 