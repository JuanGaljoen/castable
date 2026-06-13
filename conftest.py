# Ensures the repo root is on sys.path so `import ringcad` works under pytest
# without an editable install. Pytest inserts the rootdir (dir of this file)
# into sys.path because a conftest.py lives here.
