"""Repo-root entrypoint: starts the Flask app (routes live in ringcad/app.py)."""
from ringcad.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
