# Contributing

PRs are welcome. The maintainer reads issues; include a small spec and the steps needed to reproduce a problem. Remove private copy from examples before sharing them.

Build and run the tests from the repository directory:

```sh
python3 build.py examples/announcement.json review.html
python3 -m unittest discover -s tests -v
```

The builder needs only Python 3. Install Node.js 18 or later to run all JavaScript checks through `unittest`; four tests skip without it. Open the built page in a browser to check layout, keyboard navigation, saving, and copying. Test both `en` and `zh-CN` when changing interface strings. Keep the page self-contained and offline.

Before merge, comment on your pull request:

> I have read the CLA and I agree to it.

Read the full [CLA](CLA.md). You only need to agree once per project. Contributions are released under [GPL-3.0-only](LICENSE).
