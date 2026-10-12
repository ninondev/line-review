// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Ninon
// Minimal DOM fixture for executing the full inline script without a browser.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));

class Element {
  constructor(tag, document) {
    this.tagName = tag;
    this.document = document;
    this.children = [];
    this.attrs = {};
    this.listeners = {};
    this.dataset = {};
    this._text = '';
    this.value = '';
    this.hidden = false;
    this.className = '';
    this.classList = {
      toggle: (name, force) => {
        const classes = new Set(this.className.split(' ').filter(Boolean));
        const on = force === undefined ? !classes.has(name) : force;
        on ? classes.add(name) : classes.delete(name);
        this.className = [...classes].join(' ');
      }
    };
  }
  set id(value) { this._id = value; this.document.ids.set(value, this); }
  get id() { return this._id; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(x => x.textContent).join(''); }
  append(...children) { this.children.push(...children); }
  appendChild(child) { this.append(child); return child; }
  setAttribute(key, value) { this.attrs[key] = value; }
  getAttribute(key) { return this.attrs[key]; }
  addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
  dispatch(name) { for (const fn of this.listeners[name] || []) fn(); }
  click() { this.dispatch('click'); }
  focus() { this.document.activeElement = this; }
  select() { this.selected = true; }
  matches(selector) {
    if (selector === '[data-ui]') return Boolean(this.dataset.ui);
    if (selector.startsWith('.')) return selector.slice(1).split('.').every(x => this.className.split(' ').includes(x));
    return this.tagName === selector;
  }
  querySelectorAll(selector) {
    const result = [];
    for (const child of this.children) {
      if (child.matches(selector)) result.push(child);
      result.push(...child.querySelectorAll(selector));
    }
    return result;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}

function openPage(page, storage, failStorage = false) {
  const document = {
    ids: new Map(), activeElement: null,
    createElement(tag) { return new Element(tag, this); },
    createTextNode(text) { const el = new Element('#text', this); el.textContent = text; return el; },
    getElementById(id) { return this.ids.get(id); },
    querySelectorAll(selector) { return this.root.querySelectorAll(selector); }
  };
  document.root = document.createElement('root');
  document.title = input.title;
  for (const id of ['app', 'nav', 'list', 'status', 'total', 'flagged', 'only', 'export', 'out', 'outlabel', 'outtext', 'picks', 'picksnote', 'picklist']) {
    const el = document.createElement(id === 'outtext' ? 'textarea' : 'div');
    el.id = id;
    document.root.append(el);
  }
  document.getElementById('only').setAttribute('aria-pressed', 'false');
  for (const key of ['marked', 'only', 'copy', 'picksHeading', 'empty']) {
    const el = document.createElement('span'); el.dataset.ui = key; document.root.append(el);
  }
  for (const match of page.matchAll(/<script type="application\/json" id="([^"]+)">([\s\S]*?)<\/script>/g)) {
    const el = document.createElement('script'); el.id = match[1]; el.textContent = match[2]; document.root.append(el);
  }
  const context = vm.createContext({document, navigator: {}, localStorage: {
    getItem(key) { if (failStorage) throw Error('blocked'); return storage.get(key) || null; },
    setItem(key, value) { if (failStorage) throw Error('blocked'); storage.set(key, value); }
  }});
  vm.runInContext(page.match(/<script>([\s\S]*?)<\/script>/)[1], context);
  return document;
}

const storage = new Map();
let doc = openPage(input.page, storage);
assert.equal(doc.getElementById('list').querySelectorAll('.row').length, 12);
const line = doc.getElementById('list').querySelector('.line');
assert.equal(line.textContent, input.literal);
assert.equal(line.querySelector('b'), null);
assert.equal(doc.getElementById('nav').attrs['aria-label'], 'Sections');
const mark = doc.getElementById('list').querySelector('.mark');
mark.click();
assert.equal(mark.attrs['aria-pressed'], 'true');
assert.equal(doc.activeElement.id, 'note-announcement.1');
doc.activeElement.value = 'Exact input\nSecond line.';
doc.activeElement.dispatch('input');
const candidate = doc.getElementById('picklist').querySelector('.opt');
candidate.click();
assert.equal(candidate.attrs['aria-pressed'], 'true');
doc.getElementById('only').click();
assert.equal(doc.getElementById('only').attrs['aria-pressed'], 'true');
assert.ok(doc.getElementById('app').className.includes('hide-unflagged'));
doc.getElementById('export').click();
assert.ok(doc.getElementById('outtext').value.includes('My wording: Exact input\nSecond line.'));
assert.ok(doc.getElementById('outtext').value.includes('Selected: Pocket List holds your shopping list.'));
assert.equal(doc.activeElement.id, 'outtext');
assert.equal(doc.activeElement.selected, true);
assert.ok(doc.getElementById('status').textContent.includes('Ctrl+C'));
// An unmarked line retains its note and is explicitly described in the export.
mark.click();
doc.getElementById('export').click();
assert.ok(doc.getElementById('outtext').value.includes('[announcement.1] (unmarked)'));
doc = openPage(input.page, storage);
assert.equal(doc.getElementById('note-announcement.1'), undefined);
assert.equal(doc.getElementById('picklist').querySelector('.opt').attrs['aria-pressed'], 'true');
doc.getElementById('list').querySelector('.mark').click();
assert.equal(doc.getElementById('note-announcement.1').value, 'Exact input\nSecond line.');
doc = openPage(input.rebuilt, storage);
assert.equal(doc.getElementById('flagged').textContent, '0');
assert.equal(doc.getElementById('picklist').querySelector('.opt').attrs['aria-pressed'], 'false');
doc = openPage(input.chinese, new Map(), true);
assert.equal(doc.getElementById('nav').attrs['aria-label'], '分区');
doc.getElementById('list').querySelector('.mark').click();
assert.equal(doc.getElementById('status').textContent, '这里无法保存标记，关闭前请复制审阅结果。');
doc.getElementById('export').click();
assert.ok(doc.getElementById('outtext').value.startsWith('审阅结果：'));
process.stdout.write('Full inline script checks passed (DOM fixture; no visual rendering).\n');
