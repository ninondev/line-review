# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ninon
import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build


def sample():
    return json.loads((ROOT / 'examples/announcement.json').read_text(encoding='utf-8'))


def payload(page, name):
    return json.loads(re.search(r'<script type="application/json" id="' + name + r'">(.*?)</script>', page, re.S)[1])


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.script_ids = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == 'script':
            self.script_ids.append(dict(attrs).get('id'))


class BuildTests(unittest.TestCase):
    def test_sample_shape_and_defaults(self):
        spec = sample()
        self.assertEqual(len(spec['items']), 12)
        self.assertEqual(len(spec['sections']), 2)
        self.assertEqual(len(spec['picks']), 1)
        del spec['lang']
        self.assertEqual(payload(build.render(spec), 'meta')['lang'], 'en')

    def test_both_languages(self):
        for lang in ('en', 'zh-CN'):
            with self.subTest(lang=lang):
                spec = sample()
                spec['lang'] = lang
                page = build.render(spec)
                self.assertIn(f'<html lang="{lang}">', page)
                self.assertEqual(payload(page, 'meta')['lang'], lang)

    def test_invalid_spec(self):
        changes = [
            lambda s: s.update(title=''), lambda s: s.update(intro=None),
            lambda s: s.update(lang='fr'), lambda s: s.update(sections=[]),
            lambda s: s.update(items={}), lambda s: s.update(picks_note=3),
            lambda s: s['sections'].append(copy.deepcopy(s['sections'][0])),
            lambda s: s['sections'][0].update(id='a" onclick="bad'),
            lambda s: s['items'].append(copy.deepcopy(s['items'][0])),
            lambda s: s['items'][0].update(id='</script>'),
            lambda s: s['items'][0].update(sec='missing'),
            lambda s: s['items'][0].update(group=None),
            lambda s: s['items'][0].update(text=3),
            lambda s: s['items'][0].update(own='true'),
            lambda s: s['items'][0].update(hint=[]),
            lambda s: s['picks'][0].update(key='missing'),
            lambda s: s['picks'][0].update(old='different'),
            lambda s: s['picks'][0].update(options=[]),
            lambda s: s['picks'][0].update(options=[3]),
            lambda s: s['picks'].append(copy.deepcopy(s['picks'][0])),
        ]
        for i, change in enumerate(changes):
            with self.subTest(case=i):
                spec = sample()
                change(spec)
                with self.assertRaises(ValueError):
                    build.render(spec)
        for invalid in (None, [], {}, {'title': 'x'}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                build.render(invalid)

    def test_empty_items_and_optional_fields(self):
        spec = sample()
        spec.update(items=[], picks=[])
        self.assertEqual(payload(build.render(spec), 'data'), [])
        spec = sample()
        spec.pop('picks')
        spec['items'][0]['own'] = True
        self.assertEqual(payload(build.render(spec), 'picksdata'), [])

    def test_html_escaping_and_placeholder_text(self):
        spec = sample()
        nasty = '</script><b>literal & text</b> __DATA__ __TITLE__'
        spec['title'] = nasty
        spec['intro'] = nasty
        spec['sections'][0]['note'] = nasty
        spec['items'][0]['text'] = nasty
        spec['picks'][0]['old'] = nasty
        spec['picks'][0]['options'][0] = nasty
        page = build.render(spec)
        self.assertIn('&lt;/script&gt;&lt;b&gt;', page)
        self.assertNotIn('<b>literal', page)
        self.assertEqual(payload(page, 'data')[0]['text'], nasty)
        self.assertEqual(payload(page, 'picksdata')[0]['options'][0], nasty)
        parser = PageParser()
        parser.feed(page)
        self.assertEqual(parser.script_ids, ['meta', 'data', 'picksdata', None])
        self.assertEqual(parser.tags.count('html'), 1)
        self.assertEqual(page.count('</html>'), 1)
        # The runtime inserts all spec content through text nodes, never HTML.
        self.assertNotIn('innerHTML', page)
        self.assertIn('document.createTextNode(p)', page)

    def test_storage_key_changes_on_immediate_rebuild(self):
        a, b = (build.render(sample()) for _ in range(2))
        self.assertNotEqual(payload(a, 'meta')['built'], payload(b, 'meta')['built'])
        self.assertIn("const KEY = 'line-review:' + meta.built;", a)

    def test_no_external_urls_or_runtime_services(self):
        page = build.render(sample())
        self.assertIsNone(re.search(r'(?:https?:)?//|(?:src|href)\s*=\s*["\'](?:https?:|//)|url\s*\(', page))
        for forbidden in ('fetch(', 'XMLHttpRequest', 'WebSocket', '<link'):
            self.assertNotIn(forbidden, page)

    def test_cli_and_invalid_input_preserves_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / 'spec.json', Path(tmp) / 'page.html'
            src.write_text(json.dumps(sample()), encoding='utf-8')
            proc = subprocess.run([sys.executable, str(ROOT / 'build.py'), str(src), str(out)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            before = out.read_bytes()
            src.write_text('{broken', encoding='utf-8')
            proc = subprocess.run([sys.executable, str(ROOT / 'build.py'), str(src), str(out)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            self.assertIn('Build failed:', proc.stderr)
            self.assertEqual(out.read_bytes(), before)

    def test_cli_rejects_overwriting_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'spec.json'
            src.write_text(json.dumps(sample()), encoding='utf-8')
            before = src.read_bytes()
            proc = subprocess.run([sys.executable, str(ROOT / 'build.py'), str(src), str(src)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(src.read_bytes(), before)


@unittest.skipUnless(shutil.which('node'), 'Node.js is needed to execute the browser export formatter')
class ExportTests(unittest.TestCase):
    def run_export(self, lang='en', flags=None, picks=None):
        page = build.render(sample())
        runtime = re.findall(r'<script>(.*?)</script>', page, re.S)[0].split('(function ()')[0]
        fixture = {'spec': sample(), 'lang': lang, 'flags': flags or [], 'picks': picks or []}
        script = runtime + '\nconst f = JSON.parse(require("fs").readFileSync(0,"utf8"));\n' + \
            'process.stdout.write(formatExport(f.spec.title, f.spec.items, f.spec.picks, new Map(f.flags), new Map(f.picks), UI[f.lang]));'
        proc = subprocess.run(['node', '-e', script], input=json.dumps(fixture), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout

    def test_full_inline_runtime_with_dom_fixture(self):
        spec = sample()
        literal = '</script><b>literal</b> {name}'
        spec['items'][0]['text'] = literal
        spec['picks'][0]['old'] = literal
        page = build.render(spec)
        rebuilt = build.render(spec)
        spec['lang'] = 'zh-CN'
        fixture = {'title': spec['title'], 'literal': literal, 'page': page,
                   'rebuilt': rebuilt, 'chinese': build.render(spec)}
        proc = subprocess.run(['node', str(ROOT / 'tests/runtime.cjs')],
                              input=json.dumps(fixture), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('Full inline script checks passed', proc.stdout)

    def test_export_mark_note_unmark_and_choice_exact(self):
        result = self.run_export(flags=[
            ['announcement.2', {'flag': True, 'note': 'Make a list.\nKeep it short.'}],
            ['announcement.3', {'flag': False, 'note': 'Keep the original.'}],
            ['announcement.4', {'flag': True, 'note': ''}],
        ], picks=[['announcement.1', {'choice': 0, 'own': 'My first line.'}]])
        self.assertEqual(result, 'Review: Pocket List announcement\n\n'
            '[announcement.2]\nOriginal: Start a list before you leave home.\nMy wording: Make a list.\nKeep it short.\n\n'
            '[announcement.3] (unmarked)\nOriginal: Add an item whenever you think of it.\nMy wording: Keep the original.\n\n'
            '[announcement.4]\nOriginal: Check off each item as it goes into your basket.\nMy wording: (not written)\n\n'
            '[Choice announcement.1]\nSelected: Pocket List holds your shopping list.\nMy own: My first line.')

    def test_export_empty_and_cleared_choices(self):
        expected = 'Review: Pocket List announcement\n\nNo marks or choices. Keep all lines as written.'
        self.assertEqual(self.run_export(), expected)
        self.assertEqual(self.run_export(flags=[['announcement.2', {'flag': False, 'note': ''}]],
            picks=[['announcement.1', {'choice': None, 'own': ''}]]), expected)

    def test_export_own_without_choice_and_chinese(self):
        result = self.run_export(lang='zh-CN', picks=[['announcement.1', {'choice': None, 'own': '自己的说法'}]])
        self.assertEqual(result, '审阅结果：Pocket List announcement\n\n[选 announcement.1]\n选了：（没选）\n我写的：自己的说法')


if __name__ == '__main__':
    unittest.main()
