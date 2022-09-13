# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""All the action we need during build"""

import json
import os
import pathlib
import shutil
import urllib.request as url_lib
from typing import List
from zipfile import ZipFile

import nox  # pylint: disable=import-error

NATIVE_SUFFIXES = (".so", ".dylib", ".pyd")

ROOT = pathlib.Path(__file__).parent
WHEEL_DIR = ROOT / "wheels"


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


def _download_wheels(session: nox.Session) -> pathlib.Path:
    for py_version in (
        "3.7",
        "3.8",
        "3.9",
        "3.10",
    ):
        session.run(
            "pip",
            "download",
            "-q",
            "--dest",
            WHEEL_DIR.as_posix(),
            "--no-deps",
            "--require-hashes",
            "--implementation",
            "cp",
            "--python-version",
            py_version,
            "-r",
            "./requirements.txt",
        )

    wheel_names = sorted(
        path.name
        for path in WHEEL_DIR.iterdir()
        if path.is_file() and path.suffix == ".whl"
    )
    for name in wheel_names:
        print("\t" + name)
    print()


def _install_wheels(session: nox.Session) -> None:
    _download_wheels(session)

    lib_dir = ROOT / "bundled" / "libs"

    for path in WHEEL_DIR.iterdir():
        if path.is_file() and path.suffix == ".whl":
            with ZipFile(path, "r") as wheel:
                for file_info in wheel.infolist():
                    if file_info.filename.lower().endswith(NATIVE_SUFFIXES):
                        print("\t" + file_info.filename)
                        so_path = wheel.extract(file_info.filename, lib_dir)
                        print("\t\t => " + so_path)


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
    with url_lib.urlopen(json_uri) as response:
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
    shutil.rmtree(ROOT / "wheels")


@nox.session()
def download_wheels(session: nox.Session) -> None:
    """Download wheels needed to build the package."""
    _download_wheels(session)


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
