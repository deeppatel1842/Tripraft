# Purpose: Checks Compose paths, volumes and dependencies plus workflow YAML without claiming live deployment.
"""Static local validation when Docker or hosted GitHub execution is unavailable."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
compose_file = ROOT / 'infra/docker/docker-compose.yml'
compose = yaml.safe_load(compose_file.read_text())
assert {'api', 'postgres', 'redis', 'worker'} <= compose['services'].keys()
for name, service in compose['services'].items():
    if 'build' in service:
        context = (compose_file.parent / service['build']['context']).resolve()
        assert (context / 'Dockerfile').is_file(), f'Invalid build context: {name}'
    for dependency in service.get('depends_on', {}):
        assert dependency in compose['services'], f'Missing dependency: {dependency}'
    for volume in service.get('volumes', []):
        source = volume.split(':', 1)[0]
        if source.startswith('.'):
            assert (compose_file.parent / source).resolve().exists(), f'Missing mount: {source}'
        else:
            assert source in compose.get('volumes', {}), f'Missing named volume: {source}'
for name in ['ci.yml', 'deploy.yml']:
    workflow = yaml.load((ROOT / 'infra/github/workflows' / name).read_text(), Loader=yaml.BaseLoader)
    assert 'on' in workflow and workflow['jobs']
    for job in workflow['jobs'].values():
        assert job['runs-on'] and job['steps']
print('Compose paths/dependencies/volumes and workflow YAML passed static validation; no live Docker/GitHub execution claimed.')
