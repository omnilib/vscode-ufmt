# µfmt: safe, atomic formatting and import sorting

[µfmt][] is a code formatter and import sorter for Python and Visual Studio Code,
built on top of [black][] and [µsort][]:

> Black makes code review faster by producing the smallest diffs possible.
  Blackened code looks the same regardless of the project you’re reading.

> μsort is a safe, minimal import sorter. Its primary goal is to make no “dangerous”
  changes to code, and to make no changes on code style.

µfmt formats files in-memory, first with µsort and then with black, before
writing any changes back to disk. This enables a combined, atomic formatting steps in
VS Code, without any chance of conflict or intermediate changes between the import
sorter and the code formatter.

Note:

- This extension requires Python version 3.8 or newer.
- The extension comes bundled with µfmt `2.1`.
  Older versions of µfmt may work, but are not supported.

## Usage

Once installed, "µfmt" will be available as a formatter for Python files
(extension id: `omnilib.ufmt`).
µfmt can be set as the default formatter by adding the following to your settings:

```json
"[python]": {
    "editor.defaultFormatter": "omnilib.ufmt"
}
```

or through the command pallete option "Format Document With...":

<img alt="Command pallete 'format document with'" src="https://github.com/omnilib/vscode-ufmt/raw/main/enable-formatwith.png" width="600px" />

<img alt="Follow-up option 'Configure default formatter'" src="https://github.com/omnilib/vscode-ufmt/raw/main/enable-setdefault.png" width="600px" />

Be sure to disable the legacy Python formatter, if enabled:

```json
"python.formatting.provider": "none"
```

## Format on Save

VS Code can automatically format your Python files when saving by adding the following
to your settings:

```json
"[python]": {
    "editor.defaultFormatter": "omnilib.ufmt",
    "editor.formatOnSave": true
}
```

## Resources

- [µfmt documentation][µfmt]
- [black documentation][black]
- [µsort documentation][µsort]

[black]: https://black.rtfd.io
[µsort]: https://usort.rtfd.io
[µfmt]: https://ufmt.omnilib.dev