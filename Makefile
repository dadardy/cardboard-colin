PY ?= python3
all: fonts specimen
fonts:
	$(PY) scripts/build.py
specimen:
	$(PY) scripts/specimen.py
zip:
	$(PY) scripts/make_zip.py
.PHONY: all fonts specimen zip
