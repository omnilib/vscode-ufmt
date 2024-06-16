.PHONY: build
build:
	rm -rf wheels
	nox -s build_package

.PHONY: deps
deps:
	nox -s update_packages

.PHONY: test
test:
	nox -s tests

.PHONY: venv
venv:
	python -m venv --clear .venv
	.venv/bin/python -m pip install -U pip -r requirements-dev.txt
	.venv/bin/python -m pip install -Ur requirements.txt
	.venv/bin/python -m pip install -Ur src/test/python_tests/requirements.txt

.PHONY: distclean
distclean:
	git clean -xfd
