# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""All the action we need during build"""

import json
import os
import pathlib
import platform
import re
import shutil
from dataclasses import dataclass
from pprint import pprint
from typing import List
from urllib.parse import urlparse
from urllib.request import urlopen
from zipfile import ZipFile

import nox  # pylint: disable=import-error

NATIVE_SUFFIXES = (".so", ".dylib", ".pyd", ".dll")

PKG_VERSION_RE = re.compile(r"^(\S+)==(\S+)")
PKG_HASH_RE = re.compile(r"\s*--hash=(\S+):(\S+)")

ROOT = pathlib.Path(__file__).parent
WHEEL_DIR = ROOT / "wheels"
REQUIREMENTS = ROOT / "requirements.txt"

PY_VERS = ("cp311", "cp310", "cp39", "cp38", "cp37", "cp37m")
PLAT_NAMES = {
    "Windows": "win",
    "Darwin": "macosx",
    "Linux": "manylinux",
}
PLAT_ARCH = {
    "Windows": {
        "arm64": (),
        "x64": ("win32", "amd64"),
    },
    "Darwin": {
        "arm64": ("arm64", "universal2"),
        "x64": ("x86_64", "intel", "universal2"),
    },
    "Linux": {
        "arm64": ("aarch64", "arm64"),
        "x64": ("x86_64", "i686"),
    },
}

SYS_NAME = platform.system()
PIP_ARCH = os.environ.get("PIP_ARCH", "")
if not PIP_ARCH:
    arch = platform.machine().lower()
    if arch in ("x86_64", "amd64"):
        PIP_ARCH = "x64"
    elif arch in ("arm64", "aarch64"):
        PIP_ARCH = "arm64"
    else:
        raise RuntimeError(f"PIP_ARCH not provided, unexpected arch {arch!r}")


@dataclass
class Hash:
    algo: str
    value: str


@dataclass
class Requirement:
    name: str
    version: str
    hashes: List[Hash]


def _requirements() -> List[Requirement]:
    """Parse requirements.txt for package name, version, and allowed hashes"""
    content = REQUIREMENTS.read_text()

    name = ""
    version = ""
    hashes: List[Hash] = []
    results: List[Requirement] = []

    for line in content.splitlines():
        hash_match = PKG_HASH_RE.match(line)
        if hash_match:
            algo, value = hash_match.groups()
            hashes.append(Hash(algo, value))
            continue

        pkg_match = PKG_VERSION_RE.match(line)
        if pkg_match:
            if name and version:
                results.append(Requirement(name, version, hashes))
                hashes = []
            name, version = pkg_match.groups()

    return results


def _find_wheels() -> List[str]:
    """Parse PyPI json data for requirements and filter to wheels for platform/arch"""
    plat_markers = [
        f"{py_ver}-{plat_name}"
        for py_ver in PY_VERS
        for plat_name in (PLAT_NAMES[SYS_NAME],)
    ]
    arch_markers = PLAT_ARCH[SYS_NAME][PIP_ARCH]
    print(SYS_NAME, plat_markers, arch_markers)

    target_urls: List[str] = []
    for req in _requirements():
        with urlopen(f"https://pypi.org/pypi/{req.name}/json") as response:
            data = json.loads(response.read())
            dists = data["releases"].get(req.version, [])

            for dist in dists:
                url = dist["url"]
                dist_markers = dist["filename"].rpartition("-")[2]
                if any(plat_marker in url for plat_marker in plat_markers) and any(
                    arch_marker in dist_markers for arch_marker in arch_markers
                ):
                    digests = dist["digests"]
                    for req_hash in req.hashes:
                        if digests.get(req_hash.algo, "") == req_hash.value:
                            target_urls.append(url)
                            break

    pprint(target_urls)
    return target_urls


def _download_wheels() -> pathlib.Path:
    """Download all relevant wheels for the target platform/arch"""
    target_urls = _find_wheels()

    WHEEL_DIR.mkdir(exist_ok=True)

    for url in target_urls:
        parts = urlparse(url)
        path = WHEEL_DIR / pathlib.Path(parts.path).name
        if path.is_file():
            continue

        print(url, "->", path)
        with urlopen(url) as response:
            path.write_bytes(response.read())


def _install_wheels(session: nox.Session) -> None:
    """Download and install wheels for the target platform/arch"""
    _download_wheels()

    lib_dir = ROOT / "bundled" / "libs"

    for path in WHEEL_DIR.iterdir():
        if path.is_file() and path.suffix == ".whl":
            with ZipFile(path, "r") as wheel:
                for file_info in wheel.infolist():
                    if file_info.filename.lower().endswith(NATIVE_SUFFIXES):
                        print("\t" + file_info.filename)
                        so_path = wheel.extract(file_info.filename, lib_dir)
                        print("\t\t => " + so_path)


def _install_bundle(session: nox.Session) -> None:
    session.install(
        "-vvv",
        "-t",
        "./bundled/libs",
        "--no-cache-dir",
        "--only-binary",
        ":all:",
        "--implementation",
        "cp",  # required to get upstream libcst wheels
        "--no-deps",
        "--upgrade",
        "-r",
        "./requirements.txt",
    )
    _install_wheels(session)


def _check_files(names: List[str]) -> None:
    for name in names:
        file_path = ROOT / name
        lines: List[str] = file_path.read_text().splitlines()
        if any(line for line in lines if line.startswith("# TODO:")):
            raise Exception(f"Please update {os.fspath(file_path)}.")


def _update_pip_packages(session: nox.Session) -> None:
    session.install("wheel", "pip-tools")
    session.run(
        "pip-compile",
        "--generate-hashes",
        "--upgrade",
        "./requirements.in",
    )
    session.run(
        "pip-compile",
        "--generate-hashes",
        "--upgrade",
        "./src/test/python_tests/requirements.in",
    )


def _get_package_data(package):
    json_uri = f"https://registry.npmjs.org/{package}"
    with urlopen(json_uri) as response:
        return json.loads(response.read())


def _update_npm_packages(session: nox.Session) -> None:
    pinned = {
        "vscode-languageclient",
        "@types/vscode",
        "@types/node",
    }
    package_json_path = pathlib.Path(__file__).parent / "package.json"
    package_json = json.loads(package_json_path.read_text(encoding="utf-8"))

    for package in package_json["dependencies"]:
        if package not in pinned:
            data = _get_package_data(package)
            latest = "^" + data["dist-tags"]["latest"]
            package_json["dependencies"][package] = latest

    for package in package_json["devDependencies"]:
        if package not in pinned:
            data = _get_package_data(package)
            latest = "^" + data["dist-tags"]["latest"]
            package_json["devDependencies"][package] = latest

    # Ensure engine matches the package
    if (
        package_json["engines"]["vscode"]
        != package_json["devDependencies"]["@types/vscode"]
    ):
        print(
            "Please check VS Code engine version and @types/vscode version in package.json."
        )

    new_package_json = json.dumps(package_json, indent=4)
    # JSON dumps uses \n for line ending on all platforms by default
    if not new_package_json.endswith("\n"):
        new_package_json += "\n"
    package_json_path.write_text(new_package_json, encoding="utf-8")
    session.run("npm", "install", external=True)


def _setup_template_environment(session: nox.Session) -> None:
    session.install("wheel", "pip-tools")
    # session.run(
    #     "pip-compile",
    #     "--generate-hashes",
    #     "--upgrade",
    #     "./requirements.in",
    # )
    # session.run(
    #     "pip-compile",
    #     "--generate-hashes",
    #     "--upgrade",
    #     "./src/test/python_tests/requirements.in",
    # )
    _install_bundle(session)


@nox.session()
def clean(session: nox.Session) -> None:
    shutil.rmtree((ROOT / "bundled" / "libs"), ignore_errors=True)
    shutil.rmtree((ROOT / "wheels"), ignore_errors=True)


@nox.session()
def find_wheels(session: nox.Session) -> None:
    """Find relevent wheels and list their URLs"""
    _find_wheels()


@nox.session()
def download_wheels(session: nox.Session) -> None:
    """Download wheels needed to build the package."""
    _download_wheels()


@nox.session()
def setup(session: nox.Session) -> None:
    """Sets up the template for development."""
    _setup_template_environment(session)


@nox.session()
def tests(session: nox.Session) -> None:
    """Runs all the tests for the extension."""
    session.install("-r", "src/test/python_tests/requirements.txt")
    session.run("pytest", "src/test/python_tests")


@nox.session()
def lint(session: nox.Session) -> None:
    """Runs linter and formatter checks on python files."""
    session.install("-r", "./requirements.txt")
    session.install("-r", "src/test/python_tests/requirements.txt")

    session.install("pylint")
    session.run("pylint", "-d", "W0511", "./bundled/tool")
    session.run(
        "pylint",
        "-d",
        "W0511",
        "--ignore=./src/test/python_tests/test_data",
        "./src/test/python_tests",
    )
    session.run("pylint", "-d", "W0511", "noxfile.py")

    # check formatting using black
    session.install("black")
    session.run("black", "--check", "./bundled/tool")
    session.run("black", "--check", "./src/test/python_tests")
    session.run("black", "--check", "noxfile.py")

    # check import sorting using isort
    session.install("isort")
    session.run("isort", "--check", "./bundled/tool")
    session.run("isort", "--check", "./src/test/python_tests")
    session.run("isort", "--check", "noxfile.py")

    # check typescript code
    session.run("npm", "run", "lint", external=True)


@nox.session()
def build_package(session: nox.Session) -> None:
    """Builds VSIX package for publishing."""
    _check_files(["README.md", "LICENSE", "SECURITY.md", "SUPPORT.md"])
    _setup_template_environment(session)
    session.run("npm", "install", external=True)
    session.run("npm", "run", "vsce-package", external=True)


@nox.session()
def update_packages(session: nox.Session) -> None:
    """Update pip and npm packages."""
    session.install("wheel", "pip-tools")
    _update_pip_packages(session)
    _update_npm_packages(session)
