# Purpose: Validates backend Python files against the Python 3.11 grammar used by CI and Docker.
"""Validate every active Python file against the Docker/CI Python 3.11 grammar."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
files = sorted((ROOT / 'services/api').rglob('*.py'))
files = [p for p in files if not any(part in {'__pycache__', '.venv', 'node_modules'} for part in p.parts)]
for path in files:
    ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path), feature_version=(3, 11))
print(f'Python 3.11 syntax: {len(files)} files passed')
