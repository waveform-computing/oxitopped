# vim: set noet sw=4 ts=4:

# External utilities
PYTHON=python
PYFLAGS=
DEST_DIR=/
PROJECT=oxitopdump

# Calculate the base names of the distribution, the location of all source,
# documentation and executable script files
NAME:=$(shell $(PYTHON) $(PYFLAGS) setup.py --name)
VER:=$(shell $(PYTHON) $(PYFLAGS) setup.py --version)
PYVER:=$(shell $(PYTHON) $(PYFLAGS) -c "import sys; print 'py%d.%d' % sys.version_info[:2]")
PY_SOURCES:=$(shell \
	$(PYTHON) $(PYFLAGS) setup.py egg_info >/dev/null 2>&1 && \
	cat $(NAME).egg-info/SOURCES.txt)
DOC_SOURCES:=$(wildcard docs/*.rst)

# Calculate the name of all outputs
DIST_EGG=dist/$(NAME)-$(VER)-$(PYVER).egg
DIST_EXE=dist/$(NAME)-$(VER).win32.exe

# Default target
all:
	@echo "make install - Install on local system"
	@echo "make doc - Generate HTML and PDF documentation"
	@echo "make source - Create source package"
	@echo "make buildegg - Generate a PyPI egg package"
	@echo "make buildexe - Generate a Windows exe installer"
	@echo "make clean - Get rid of scratch and byte files"

install:
	$(PYTHON) $(PYFLAGS) setup.py install --root $(DEST_DIR) $(COMPILE)

source: $(DIST_TAR)

buildexe: $(DIST_EXE)

buildegg: $(DIST_EGG)

dist: $(DIST_EXE) $(DIST_EGG) $(DIST_TAR)

develop: tags
	$(PYTHON) $(PYFLAGS) setup.py develop

test:
	nosetests -w tests/

clean:
	$(PYTHON) $(PYFLAGS) setup.py clean
	$(MAKE) -f $(CURDIR)/debian/rules clean
	rm -fr build/ dist/ $(NAME).egg-info/ tags distribute-*.egg distribute-*.tar.gz
	find $(CURDIR) -name "*.pyc" -delete

tags: $(PY_SOURCES)
	ctags -R --exclude="build/*" --exclude="docs/*" --languages="Python"

$(MAN_PAGES): $(DOC_SOURCES)
	$(PYTHON) $(PYFLAGS) setup.py build_sphinx -b man

$(DIST_TAR): $(PY_SOURCES)
	$(PYTHON) $(PYFLAGS) setup.py sdist $(COMPILE)

$(DIST_EGG): $(PY_SOURCES)
	$(PYTHON) $(PYFLAGS) setup.py bdist_egg $(COMPILE)

$(DIST_EXE): $(PY_SOURCES)
	$(PYTHON) $(PYFLAGS) setup.py bdist_wininst $(COMPILE)

