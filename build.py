#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ninon
"""Build a self-contained review page: python3 build.py spec.json out.html."""

import argparse
import html
import json
from pathlib import Path
import re
import sys
import uuid


ID = re.compile(r"[A-Za-z0-9_.-]+\Z")


def validate_spec(spec):
    """Reject malformed fields and unresolved references before writing output."""
    def obj(value, where):
        if not isinstance(value, dict):
            raise ValueError(f"{where} must be an object")

    def string(value, where, nonempty=False):
        if not isinstance(value, str) or (nonempty and not value.strip()):
            raise ValueError(f"{where} must be {'a nonempty' if nonempty else 'a'} string")

    def identifier(value, where):
        string(value, where, True)
        if not ID.fullmatch(value):
            raise ValueError(f"{where} may contain only letters, digits, _, . and -")

    def array(value, where, nonempty=False):
        if not isinstance(value, list) or (nonempty and not value):
            raise ValueError(f"{where} must be {'a nonempty' if nonempty else 'an'} array")

    obj(spec, "spec")
    string(spec.get("title"), "title", True)
    string(spec.get("intro"), "intro")
    if spec.get("lang", "en") not in ("en", "zh-CN"):
        raise ValueError('lang must be "en" or "zh-CN"')
    if "picks_note" in spec:
        string(spec["picks_note"], "picks_note")
    array(spec.get("sections"), "sections", True)
    sections = set()
    for section in spec["sections"]:
        obj(section, "section")
        identifier(section.get("id"), "section.id")
        if section["id"] in sections:
            raise ValueError("section ids must be unique")
        sections.add(section["id"])
        string(section.get("title"), "section.title", True)
        if "note" in section:
            string(section["note"], "section.note")

    array(spec.get("items"), "items")
    items = {}
    for item in spec["items"]:
        obj(item, "item")
        identifier(item.get("id"), "item.id")
        if item["id"] in items:
            raise ValueError("item ids must be unique")
        identifier(item.get("sec"), "item.sec")
        if item["sec"] not in sections:
            raise ValueError("item.sec must reference a section id")
        string(item.get("group"), "item.group", True)
        string(item.get("text"), "item.text")
        for key in ("ctx", "hint"):
            if key in item:
                string(item[key], f"item.{key}")
        if "own" in item and not isinstance(item["own"], bool):
            raise ValueError("item.own must be a boolean")
        items[item["id"]] = item

    array(spec.get("picks", []), "picks")
    keys = set()
    for pick in spec.get("picks", []):
        obj(pick, "pick")
        identifier(pick.get("key"), "pick.key")
        if pick["key"] in keys:
            raise ValueError("pick keys must be unique")
        keys.add(pick["key"])
        if pick["key"] not in items:
            raise ValueError("pick.key must reference an item id")
        string(pick.get("old"), "pick.old")
        if pick["old"] != items[pick["key"]]["text"]:
            raise ValueError("pick.old must match the referenced item text")
        if "ctx" in pick:
            string(pick["ctx"], "pick.ctx")
        array(pick.get("options"), "pick.options", True)
        for option in pick["options"]:
            string(option, "pick option", True)
    return spec


def script_json(value):
    # Script elements use HTML raw-text parsing, even with application/json.
    return json.dumps(value, ensure_ascii=False).replace("&", "\\u0026").replace(
        "<", "\\u003c").replace(">", "\\u003e")


def render(spec):
    validate_spec(spec)
    meta = {"sections": spec["sections"], "built": uuid.uuid4().hex,
            "lang": spec.get("lang", "en"), "picks_note": spec.get("picks_note")}
    values = {
        "LANG": meta["lang"], "TITLE": html.escape(spec["title"]),
        "INTRO": html.escape(spec["intro"]), "META": script_json(meta),
        "DATA": script_json(spec["items"]), "PICKS": script_json(spec.get("picks", [])),
    }
    template = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    # One substitution pass keeps placeholder-like user text literal.
    return re.sub(r"__(LANG|TITLE|INTRO|META|DATA|PICKS)__",
                  lambda match: values[match[1]], template)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.spec.resolve() == args.output.resolve():
            raise ValueError("input and output paths must differ")
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        page = render(spec)
        args.output.write_text(page, encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    print(f"{len(spec['items'])} lines, {len(spec.get('picks', []))} picks -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
