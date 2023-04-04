.PHONY: build
build:
	nox -s build_package

.PHONY: distclean
distclean:
	git clean -xfd
