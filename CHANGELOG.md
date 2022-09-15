vscode-ufmt
===========

v2022.9.14
----------

Bugfix release

- Fix: arm64 builds now correctly include arm64 native extensions (#18)
- Fix: stop logging stdout from ufmt, which may include file contents
- Fix: always load pygls from bundled extensions, preventing startup failures
- Fix: reload ufmt et al on every invocation to pick up environment changes (#19)
- Update bundled versions to ufmt==2.0.1 and usort==1.0.5

```
$ git shortlog -s v2022.9.6...v2022.9.14
     7	Amethyst Reese
```


v2022.9.6
---------

Feature release

- Build and publish platform/OS/arch specific packages for VS Code (#6)
- Bundle native extensions for all supported Python versions (#16)
- Updated project URLs to point to vscode-ufmt (#5)

```
$ git shortlog -s v2022.9.5...v2022.9.6
     2	Amethyst Reese
```


v2022.9.5
---------

Feature release

- Build and publish platform/OS/arch specific packages for VS Code (#6)
- Bundle native extensions for all supported Python versions (#16)
- Updated project URLs to point to vscode-ufmt (#5)

```
$ git shortlog -s v2022.8.5...v2022.9.5
     6	Amethyst Reese
     1	John Reese
     5	dependabot[bot]
```


v2022.8.5
---------

Initial release

- New "µfmt" formatter based on VS Code extension template

```
$ git shortlog -s v2022.8.5
     7	John Reese
```

