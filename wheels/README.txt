Windows wheel cache
====================

No binary wheels are bundled in the source tree. On Windows with Python 3.11, populate this folder with:

  python -m pip download -r requirements.txt -d wheels --platform win_amd64 --python-version 311 --only-binary=:all:

start.bat installs from this folder when it contains wheel files and falls back to PyPI if the offline install is unavailable.
