.PHONY: build
build:
	nox -s build_package

.PHONY: deps
deps:
	nox -s update_packages

.PHONY: test
test:
	nox -s tests

.PHONY: distclean
distclean:
	git clean -xfd
