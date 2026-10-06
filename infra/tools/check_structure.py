# Purpose: Checks required workspace files, discovered workflows, and Python/JavaScript/TypeScript import targets.
"""Guard monorepo paths, workflow discovery copies, and archived source retention."""
import json
import ast
import re
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
required = ['apps/web/src/main.tsx', 'apps/admin/src/main.tsx', 'services/api/app/core/factory.py',
            'services/api/migrations', 'services/api/tests', 'packages/ui', 'packages/api-client',
            'packages/types', 'packages/config', 'data/seeds', 'infra/docker/docker-compose.yml',
            'infra/terraform', 'docs/architecture.md', 'docs/api.md', 'docs/runbook.md',
            'pnpm-workspace.yaml', 'turbo.json', 'README.md', 'start.py', 'docs/files.md']
for name in required:
    assert (ROOT / name).exists(), f'Missing {name}'
for name in ['ci.yml', 'deploy.yml']:
    assert (ROOT / 'infra/github/workflows' / name).read_bytes() == (ROOT / '.github/workflows' / name).read_bytes(), f'Run pnpm workflows:sync: {name}'
manifest = ROOT / 'extra/history/path-migration.json'
mapping = json.loads(manifest.read_text(encoding='utf-8')) if manifest.is_file() else {}
for original, current in mapping.items():
    assert (ROOT / current).is_file(), f'Missing preserved source for {original}: {current}'
python_count = 0
for file in (ROOT / 'services/api').rglob('*.py'):
    if '__pycache__' in file.parts:
        continue
    for node in ast.walk(ast.parse(file.read_text(encoding='utf-8-sig'))):
        modules = [node.module] if isinstance(node, ast.ImportFrom) and node.module else [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
        for module in modules:
            if module.startswith('app.'):
                target = ROOT / 'services/api' / module.replace('.', '/')
                assert target.is_dir() or target.with_suffix('.py').is_file(), f'Broken Python import {module} in {file}'
                python_count += 1
js_count = 0
for base in ['apps/web', 'apps/admin', 'packages/ui']:
    candidates = []
    for folder, directories, names in os.walk(ROOT / base):
        directories[:] = [name for name in directories if name not in {'node_modules', 'dist', '.turbo'}]
        candidates.extend(Path(folder) / name for name in names)
    for file in candidates:
        if file.suffix not in {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}:
            continue
        source = file.read_text(encoding='utf-8-sig')
        for spec in re.findall(r'''(?:\bfrom\s*|\bimport\s*\(\s*|\bimport\s*|\brequire\(\s*|\bjest\.mock\(\s*)['"](\.[^'"]+)['"]''', source):
            target = (file.parent / spec).resolve()
            candidates = [target] + [Path(str(target) + ext) for ext in ('.js', '.jsx', '.ts', '.tsx', '.cjs', '.mjs', '.d.ts')] + [target / ('index' + ext) for ext in ('.js', '.jsx', '.ts', '.tsx')]
            assert any(candidate.is_file() for candidate in candidates), f'Broken relative import {spec} in {file}'
            js_count += 1
print(f'Structure passed: {len(mapping)} preserved files; {python_count} Python and {js_count} relative JavaScript/TypeScript import references.')
