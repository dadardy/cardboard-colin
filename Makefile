PY ?= python3
all: fonts specimen
fonts:
	$(PY) scripts/build.py
specimen:
	$(PY) scripts/specimen.py
zip:
	mkdir -p dist && rm -f dist/CardboardColin-v1.0.0.zip && zip -r dist/CardboardColin-v1.0.0.zip fonts OFL.txt README.md css
.PHONY: all fonts specimen zip
