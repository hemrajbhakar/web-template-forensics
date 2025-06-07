import re
import json
from collections import defaultdict
from typing import Dict, Tuple, List
import tinycss2

class CSSStyleChecker:
    def parse_css(self, css_content: str, parent_media=None, parent_supports=None):
        """
        Parse CSS into:
        - selector -> {property: (value, important)} for top-level rules
        - media_query -> selector -> {property: (value, important)} for @media rules
        - keyframes: name -> {step: {prop: value}}
        - supports: condition -> selector -> {property: (value, important)}
        - root_vars: {--var: value}
        Handles nested @media and @supports via recursion.
        """
        stylesheet = tinycss2.parse_stylesheet(css_content, skip_comments=True, skip_whitespace=True)
        rules = defaultdict(dict)
        media_rules = defaultdict(lambda: defaultdict(dict))
        keyframes = defaultdict(lambda: defaultdict(dict))
        supports = defaultdict(lambda: defaultdict(dict))
        root_vars = {}
        for rule in stylesheet:
            if rule.type == 'qualified-rule':
                selector = tinycss2.serialize(rule.prelude).strip()
                declarations = tinycss2.parse_declaration_list(rule.content)
                for decl in declarations:
                    if decl.type == 'declaration':
                        prop = decl.name
                        val = tinycss2.serialize(decl.value).strip()
                        important = decl.important
                        if parent_media and parent_supports:
                            supports[parent_supports][selector][prop] = (val, important)
                            media_rules[parent_media][selector][prop] = (val, important)
                        elif parent_media:
                            media_rules[parent_media][selector][prop] = (val, important)
                        elif parent_supports:
                            supports[parent_supports][selector][prop] = (val, important)
                        else:
                            rules[selector][prop] = (val, important)
                        if selector == ':root' and prop.startswith('--'):
                            root_vars[prop] = val
            elif rule.type == 'at-rule' and rule.lower_at_keyword == 'media' and rule.content:
                media_query = tinycss2.serialize(rule.prelude).strip()
                # Recursively parse nested rules
                sub_rules, sub_media, sub_keyframes, sub_supports, sub_vars = self.parse_css(
                    tinycss2.serialize(rule.content), parent_media=media_query, parent_supports=parent_supports)
                # Merge results
                for sel, props in sub_rules.items():
                    media_rules[media_query][sel].update(props)
                for mq, sel_dict in sub_media.items():
                    for sel, props in sel_dict.items():
                        media_rules[mq][sel].update(props)
                for kf, steps in sub_keyframes.items():
                    keyframes[kf].update(steps)
                for cond, sel_dict in sub_supports.items():
                    for sel, props in sel_dict.items():
                        supports[cond][sel].update(props)
                root_vars.update(sub_vars)
            elif rule.type == 'at-rule' and rule.lower_at_keyword == 'keyframes' and rule.content:
                kf_name = tinycss2.serialize(rule.prelude).strip()
                for subrule in tinycss2.parse_rule_list(rule.content):
                    if subrule.type == 'qualified-rule':
                        step = tinycss2.serialize(subrule.prelude).strip()
                        declarations = tinycss2.parse_declaration_list(subrule.content)
                        for decl in declarations:
                            if decl.type == 'declaration':
                                prop = decl.name
                                val = tinycss2.serialize(decl.value).strip()
                                keyframes[kf_name][step][prop] = val
            elif rule.type == 'at-rule' and rule.lower_at_keyword == 'supports' and rule.content:
                cond = tinycss2.serialize(rule.prelude).strip()
                # Recursively parse nested rules
                sub_rules, sub_media, sub_keyframes, sub_supports, sub_vars = self.parse_css(
                    tinycss2.serialize(rule.content), parent_media=parent_media, parent_supports=cond)
                for sel, props in sub_rules.items():
                    supports[cond][sel].update(props)
                for mq, sel_dict in sub_media.items():
                    for sel, props in sel_dict.items():
                        media_rules[mq][sel].update(props)
                for kf, steps in sub_keyframes.items():
                    keyframes[kf].update(steps)
                for cond2, sel_dict in sub_supports.items():
                    for sel, props in sel_dict.items():
                        supports[cond2][sel].update(props)
                root_vars.update(sub_vars)
        return dict(rules), dict(media_rules), dict(keyframes), dict(supports), root_vars

    def resolve_vars(self, value, root_vars, seen=None):
        # Replace var(--...) with value from root_vars, support recursion and fallback
        if seen is None:
            seen = set()
        def repl(match):
            varname = match.group(1)
            fallback = match.group(2)
            if varname in seen:
                return f"var({varname})"  # Prevent infinite recursion
            seen.add(varname)
            resolved = root_vars.get(varname)
            if resolved is not None:
                return self.resolve_vars(resolved, root_vars, seen)
            elif fallback is not None:
                return fallback.strip()
            else:
                return f"var({varname})"
        # Handles var(--x, fallback)
        return re.sub(r'var\((--[\w-]+)(?:,\s*([^\)]+))?\)', repl, value)

    def normalize_color(self, value):
        # Normalize #fff and #ffffff, lowercase, remove spaces
        value = value.strip().lower().replace(' ', '')
        hex_match = re.fullmatch(r'#([0-9a-f]{3,8})', value)
        if hex_match:
            hexval = hex_match.group(1)
            if len(hexval) == 3:
                value = '#' + ''.join([c*2 for c in hexval])
            elif len(hexval) == 4:
                value = '#' + ''.join([c*2 for c in hexval])  # rgba short
            return value
        return value

    def normalize_number(self, value):
        # Normalize 10px == 10.0px, 1em == 1.0em
        match = re.fullmatch(r'([+-]?\d*\.?\d+)([a-z%]*)', value.strip().lower())
        if match:
            num, unit = match.groups()
            try:
                num = float(num)
                if num.is_integer():
                    num = int(num)
                return f"{num}{unit}"
            except Exception:
                pass
        return value.strip().lower()

    def normalize_value(self, value):
        # Normalize for comparison: color, number, etc.
        value = self.normalize_color(value)
        value = self.normalize_number(value)
        return value

    def specificity(self, selector: str) -> int:
        # IDs
        id_count = len(re.findall(r'#[\w-]+', selector))
        # Classes
        class_count = len(re.findall(r'\.[\w-]+', selector))
        # Attribute selectors
        attr_count = len(re.findall(r'\[[^\]]+\]', selector))
        # Pseudo-elements (double colon)
        pseudo_element_count = len(re.findall(r'::[\w-]+', selector))
        # Pseudo-classes (single colon, not part of pseudo-element)
        pseudo_class_count = len(re.findall(r':(?!:)[\w-]+', selector))
        # Element names (not part of class, id, attribute, or pseudo)
        # This is a rough approximation
        element_count = len(re.findall(r'(^|\s|\+|~|>)\w+', selector))
        return (
            100 * id_count +
            10 * (class_count + attr_count + pseudo_class_count) +
            1 * (element_count + pseudo_element_count)
        )

    def compare_rule_dicts(self, rules1, rules2, root_vars1, root_vars2) -> Tuple[int, int, int, int, float]:
        selectors1 = set(rules1.keys())
        selectors2 = set(rules2.keys())
        matching = selectors1 & selectors2
        missing = selectors1 - selectors2
        extra = selectors2 - selectors1
        different = 0
        specificity_score = 0.0
        total_specificity = 0.0
        for sel in matching:
            props1 = rules1[sel]
            props2 = rules2[sel]
            all_props = set(props1.keys()) | set(props2.keys())
            sel_spec = self.specificity(sel)
            total_specificity += sel_spec
            sel_match = True
            imp_mismatch = False
            for prop in all_props:
                v1, imp1 = props1.get(prop, (None, False))
                v2, imp2 = props2.get(prop, (None, False))
                # Resolve variables
                if v1 and 'var(' in v1:
                    v1 = self.resolve_vars(v1, root_vars1)
                if v2 and 'var(' in v2:
                    v2 = self.resolve_vars(v2, root_vars2)
                v1 = self.normalize_value(v1) if v1 else v1
                v2 = self.normalize_value(v2) if v2 else v2
                if v1 != v2 or imp1 != imp2:
                    sel_match = False
                    if imp1 != imp2:
                        imp_mismatch = True
            if sel_match:
                specificity_score += sel_spec
            elif imp_mismatch:
                specificity_score += 0.2 * sel_spec  # Lower score for !important mismatch
                different += 1
            else:
                specificity_score += 0.5 * sel_spec
                different += 1
        for sel in missing | extra:
            total_specificity += self.specificity(sel)
        return len(matching), different, len(missing), len(extra), specificity_score / total_specificity if total_specificity else 0.0

    def compare_keyframes(self, kf1, kf2):
        names1 = set(kf1.keys())
        names2 = set(kf2.keys())
        matching = names1 & names2
        missing = names1 - names2
        extra = names2 - names1
        different = 0
        details = {}
        for name in matching:
            steps1 = kf1[name]
            steps2 = kf2[name]
            all_steps = set(steps1.keys()) | set(steps2.keys())
            step_diff = 0
            for step in all_steps:
                props1 = steps1.get(step, {})
                props2 = steps2.get(step, {})
                # Normalize values for keyframes
                norm1 = {k: self.normalize_value(v) for k, v in props1.items()}
                norm2 = {k: self.normalize_value(v) for k, v in props2.items()}
                if norm1 != norm2:
                    step_diff += 1
            if step_diff:
                different += 1
            details[name] = {'step_differences': step_diff, 'total_steps': len(all_steps)}
        return {
            'matching_keyframes': len(matching),
            'different_keyframes': different,
            'missing_keyframes': len(missing),
            'extra_keyframes': len(extra),
            'details': details
        }

    def compare_supports(self, s1, s2, root_vars1, root_vars2):
        conds1 = set(s1.keys())
        conds2 = set(s2.keys())
        matching = conds1 & conds2
        missing = conds1 - conds2
        extra = conds2 - conds1
        details = {}
        for cond in matching:
            m, d, miss, extra_sel, _ = self.compare_rule_dicts(s1[cond], s2[cond], root_vars1, root_vars2)
            details[cond] = {
                'matching_selectors': m,
                'different_selectors': d,
                'missing_selectors': miss,
                'extra_selectors': extra_sel
            }
        return {
            'matching_supports': len(matching),
            'missing_supports': len(missing),
            'extra_supports': len(extra),
            'details': details
        }

    def compare_css(self, css1: str, css2: str) -> Dict:
        rules1, media1, kf1, supports1, root_vars1 = self.parse_css(css1)
        rules2, media2, kf2, supports2, root_vars2 = self.parse_css(css2)
        # Top-level rules
        m, d, miss, extra, spec_score = self.compare_rule_dicts(rules1, rules2, root_vars1, root_vars2)
        # Media queries
        all_media = set(media1.keys()) | set(media2.keys())
        media_results = {}
        for mq in all_media:
            mq_rules1 = media1.get(mq, {})
            mq_rules2 = media2.get(mq, {})
            mm, md, mmiss, mextra, mspec_score = self.compare_rule_dicts(mq_rules1, mq_rules2, root_vars1, root_vars2)
            media_results[mq] = {
                "matching_selectors": mm,
                "different_selectors": md,
                "missing_selectors": mmiss,
                "extra_selectors": mextra,
                "similarity": round(mspec_score, 2)
            }
        # Keyframes
        keyframes_result = self.compare_keyframes(kf1, kf2)
        # Supports
        supports_result = self.compare_supports(supports1, supports2, root_vars1, root_vars2)
        summary = f"{m} matching selectors; {d} differ in declarations; {miss} missing; {extra} extra"
        if media_results:
            summary += "; Media queries: " + ", ".join(f"{mq}: {v['matching_selectors']} match, {v['different_selectors']} differ" for mq, v in media_results.items())
        if keyframes_result['matching_keyframes'] or keyframes_result['different_keyframes']:
            summary += f"; Keyframes: {keyframes_result['matching_keyframes']} match, {keyframes_result['different_keyframes']} differ"
        if supports_result['matching_supports'] or supports_result['missing_supports'] or supports_result['extra_supports']:
            summary += f"; Supports: {supports_result['matching_supports']} match, {supports_result['missing_supports']} missing, {supports_result['extra_supports']} extra"
        return {
            "css_similarity": round(spec_score, 2),
            "matching_selectors": m,
            "different_selectors": d,
            "missing_selectors": miss,
            "extra_selectors": extra,
            "media_queries": media_results,
            "keyframes": keyframes_result,
            "supports": supports_result,
            "summary": summary
        } 