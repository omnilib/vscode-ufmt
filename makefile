.PHONY: build
build:
	uvx nox -s build_package

.PHONY: deps
deps:
	uvx nox -s update_packages

.PHONY: test
test:
	uvx nox -s tests

.PHONY: venv
venv:
	uv venv --clear .venv
	uv pip install -U pip -r requirements-dev.txt
	uv pip install -Ur requirements.txt
	uv pip install -Ur src/test/python_tests/requirements.txt

.PHONY: clean
clean:
	rm -rf wheels/ *.vsix

.PHONY: distclean
distclean:
	git clean -xfd
