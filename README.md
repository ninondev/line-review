# line-review

Give the writer the exact line you want changed.

line-review turns a JSON draft into one offline HTML page for reviewing AI-written copy. Open the [sample page](examples/announcement.html): it contains 12 lines in two sections and one choice between three rewrites. A marked line comes back as plain text:

```text
Review: Pocket List announcement

[announcement.2]
Original: Start a list before you leave home.
My wording: Make a list.
```

Marks stay in that browser on that machine. Every rebuild starts a fresh review, even with the same spec and filename. Copy your results before rebuilding or clearing browser data. The page uses system fonts, loads no external resources, and sends nothing anywhere.

## Build a page

You need Python 3. The builder uses only the standard library.

```sh
python3 build.py examples/announcement.json review.html
```

Open `review.html` in a browser. You can also open the included sample without running Python. The page needs JavaScript enabled; it does not need a server or internet access.

## Write a spec

Put each line of copy in an item. Use sections for where the copy appears and groups for nearby lines. Everything is plain text, including strings that look like HTML.

```json
{
  "lang": "en",
  "title": "Shopping list draft",
  "intro": "Mark any line you would change.",
  "sections": [
    {"id": "opening", "title": "Opening", "note": "Product page."}
  ],
  "items": [
    {
      "id": "opening.1",
      "sec": "opening",
      "group": "intro",
      "ctx": "First sentence",
      "text": "Keep your shopping list on this device.",
      "hint": "Appears below the title.",
      "own": false
    }
  ],
  "picks": [
    {
      "key": "opening.1",
      "ctx": "First sentence",
      "old": "Keep your shopping list on this device.",
      "options": ["Your shopping list stays on this device.", "Save your list here."]
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `lang` | UI and export language: `en` or `zh-CN` (Simplified Chinese). Defaults to `en`. It does not translate your copy. |
| `title`, `intro` | Required strings. The title must not be blank. |
| `sections` | A nonempty array of sections with unique `id` values and nonblank `title` values. `note` is optional. |
| `items` | An array of lines. Each needs a unique `id`, a `sec` that names a section, a nonblank `group`, and `text`. An empty array is allowed. |
| `ctx`, `hint`, `own` | Optional item fields. `ctx` labels a group; `hint` adds context under the line. `own: true` adds a “Your words” badge. |
| `picks` | Optional array of candidate rewrites. Each `key` names an item, `old` matches its text, and `options` contains nonblank strings. Each item can have one picks entry. `ctx` is optional. |
| `picks_note` | Optional text above the candidates, replacing the default instruction. |

IDs use letters, digits, underscores, periods, and hyphens. Keep a group's items together within its section. The builder validates the spec before writing the output. See [the full example](examples/announcement.json) for a fictional product announcement.

## Review the copy

1. Open the HTML file and read each line. Press **Edit** beside a line to mark it. Write replacement wording or an instruction in the field underneath, if needed.
2. Press **Show marked only** to filter the reading list. Press a candidate to select it; press it again to clear the choice. No candidate is selected by default. You can also write your own candidate.
3. Press **Copy review** and paste the text back to the writer. If the browser blocks clipboard access, the page selects the export text for manual copying with Ctrl+C or Command+C.

Buttons work with Tab and Enter or Space. Marking a line moves focus to its wording field. A status message tells you whether the browser saved the marks. If saving is blocked, copy the review before closing the page.

## Export format

The export starts with `Review: <title>`, followed by blank-line-separated entries in spec order. A line entry contains its ID, original text, and the reviewer's wording. A mark without wording uses `(not written)`. If you remove a mark but leave a note, the entry includes `(unmarked)` and preserves the note.

A candidate entry looks like this:

```text
[Choice announcement.1]
Selected: Pocket List holds your shopping list.
My own: My first line.
```

An unselected candidate with your own wording uses `(not selected)`. If you supply both a candidate and your own wording, the export includes both; the writer should resolve which wording to use. Cleared choices with no wording are omitted. When nothing is marked or chosen, the export says `No marks or choices. Keep all lines as written.` The Chinese UI exports the same structure with Chinese labels. Multiline wording keeps its line breaks. This format is for a person or agent to read, not a machine interchange format.

## Limits

The page does not edit the source draft. The writer applies the returned instructions. Marks use `localStorage`; they do not sync between browsers, machines, or reviewers. Local-file storage behavior varies by browser, and moving or renaming a page can make previous marks unavailable. Private browsing or storage restrictions can prevent saving. Rebuilding creates a new storage key and leaves older keys in the browser. Export before replacing a page.

## Test and contribute

```sh
python3 -m unittest discover -s tests -v
```

Tests use stdlib `unittest`. Node.js 18 or later runs the inline JavaScript export checks and a small DOM fixture for the full script. Those four tests skip when Node is missing. The fixture checks behavior, not browser layout or actual clipboard access.

PRs are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CLA.md](CLA.md) before contributing. Licensed under [GPL-3.0-only](LICENSE).

For your next draft, copy the example spec, replace its fictional copy, and build a new page.

If this was useful to you, a star helps other people find it.
