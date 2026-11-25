"""Prints the API's OpenAPI description, for the web client's generated types.

Usage: python -m scripts.generate_openapi > openapi.json
"""

import json
import sys

from baja.app import app

if __name__ == "__main__":
    json.dump(app.openapi(), sys.stdout, indent=2, sort_keys=True)
