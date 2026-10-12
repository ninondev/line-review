# Contributing

PRs are welcome. The maintainer reads issues; include a small spec and the steps needed to reproduce a problem. Remove private copy from examples before sharing them.

Build and run the tests from the repository directory:

```sh
python3 build.py examples/announcement.json review.html
python3 -m unittest discover -s tests -v
```

The builder needs only Python 3. Install Node.js 18 or later to run all JavaScript checks through `unittest`; four tests skip without it. Open the built page in a browser to check layout, keyboard navigation, saving, and copying. Test both `en` and `zh-CN` when changing interface strings. Keep the page self-contained and offline.

Contributions are released under the [MIT License](LICENSE).
