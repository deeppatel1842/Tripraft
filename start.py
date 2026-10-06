#!/usr/bin/env python3
# Purpose: Sets up isolated dependencies once, starts API/web/admin, checks readiness, and stops only its owned services.
"""Set up once, then start TripRaft's API, web app, and admin console.

Usage: python start.py [--setup | --check | --smoke] [--docker] [--no-browser]
Requires Node >=22 and Python 3.11 for native mode, or Docker for Docker mode.
Only this repository's child processes are stopped; existing data is preserved.
"""
import argparse
import hashlib
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / '.tripraft'
API = ROOT / 'services/api'
VENV = ROOT / '.venv'
PNPM_VERSION = '10.34.6'
PNPM_HOME = LOCAL / 'tools/pnpm'
PNPM_SCRIPT = PNPM_HOME / 'node_modules/pnpm/bin/pnpm.cjs'
COMPOSE = ROOT / 'infra/docker/docker-compose.yml'
STATE = LOCAL / 'setup-state.json'


def run(command, *, cwd=ROOT, env=None, capture=False):
    """Run argument lists directly and report failures without exposing environment values."""
    result = subprocess.run(command, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None)
    if result.returncode:
        raise RuntimeError(f'Command failed (exit {result.returncode}): {Path(command[0]).name}. See output above.')
    return result.stdout.strip() if capture else ''


def node_runtime():
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Install Node.js 22 or newer, then run this file again.')
    version = run([node, '--version'], capture=True)
    if int(version.lstrip('v').split('.')[0]) < 22:
        raise RuntimeError(f'Node.js 22 or newer is required; found {version}.')
    return node


def python_runtime():
    """Find the pinned runtime even when Windows associates .py files with a newer Python."""
    candidates = [[sys.executable], ['py', '-3.11']] if os.name == 'nt' else [[sys.executable], ['python3.11']]
    for candidate in candidates:
        try:
            result = subprocess.run(candidate + ['-c', 'import sys; print(sys.executable); print(sys.version_info[:2] == (3, 11))'],
                                    capture_output=True, text=True)
            lines = result.stdout.strip().splitlines()
            if result.returncode == 0 and len(lines) == 2 and lines[1] == 'True':
                return lines[0]
        except OSError:
            pass
    raise RuntimeError('Install Python 3.11 for native mode, or use --docker with Docker running.')


def venv_python():
    return VENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def child_env():
    """Make local package tools available to nested pnpm/Turbo commands."""
    env = os.environ.copy()
    directories = [str(PNPM_HOME / 'node_modules/.bin'), str(venv_python().parent)]
    env['PATH'] = os.pathsep.join(directories + [env.get('PATH', '')])
    # A real isolated environment must not inherit archived dependency overrides.
    env.pop('PYTHONPATH', None)
    env['PYTHONUNBUFFERED'] = '1'
    return env


def fingerprint(docker):
    digest = hashlib.sha256(f'{PNPM_VERSION}:{docker}'.encode())
    for name in ['pnpm-lock.yaml', 'services/api/requirements.txt', 'services/api/requirements-dev.txt']:
        digest.update((ROOT / name).read_bytes())
    return digest.hexdigest()


def setup_ready(saved, docker):
    """A saved stamp is valid only while the installed entry points still exist."""
    mode = 'docker' if docker else 'native'
    return (saved.get(mode) == fingerprint(docker) and PNPM_SCRIPT.is_file()
            and (ROOT / 'apps/web/node_modules/vite/bin/vite.js').is_file()
            and (ROOT / 'apps/admin/node_modules/vite/bin/vite.js').is_file()
            and (docker or venv_python().is_file()))


def configure_native():
    """Create development settings once; never overwrite existing settings or legacy databases."""
    target = API / '.env'
    if target.exists():
        return
    values = {
        'SECRET_KEY': secrets.token_urlsafe(48),
        'JWT_SECRET_KEY': secrets.token_urlsafe(48),
        'REDIS_URL': '',
        'FLASK_HOST': '127.0.0.1',
    }
    lines = []
    for line in (API / '.env.example').read_text(encoding='utf-8').splitlines():
        key = line.split('=', 1)[0]
        lines.append(f'{key}={values[key]}' if key in values else line)
    database = ROOT / 'data/runtime/dev/tripraft.db'
    database.parent.mkdir(parents=True, exist_ok=True)
    lines += ['', '# Separate native development data; existing data/runtime/tripraft.db is preserved.',
              'DATABASE_URL=sqlite:///' + database.as_posix(),
              'TRAVEL_DATABASE_DIR=' + (ROOT / 'data/catalog').as_posix()]
    target.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    if os.name != 'nt':
        target.chmod(0o600)


def configure_docker():
    target = COMPOSE.parent / '.env'
    if not target.exists():
        target.write_text('# Generated local Docker settings; never commit this file.\n'
                          + f'POSTGRES_PASSWORD={secrets.token_hex(24)}\n'
                          + f'SECRET_KEY={secrets.token_urlsafe(48)}\nADMIN_EMAILS=\n', encoding='utf-8')
        if os.name != 'nt':
            target.chmod(0o600)


def docker_command():
    docker = shutil.which('docker')
    if not docker:
        raise RuntimeError('Install and start Docker Desktop before using --docker.')
    run([docker, 'compose', 'version'], capture=True)
    run([docker, 'info'], capture=True)
    return [docker, 'compose', '--project-directory', str(COMPOSE.parent), '-f', str(COMPOSE), '--profile', 'workers']


def setup(node, docker, force=False):
    """Install pinned tools/dependencies when missing or their manifest fingerprint changes."""
    LOCAL.mkdir(parents=True, exist_ok=True)
    mode = 'docker' if docker else 'native'
    saved = json.loads(STATE.read_text()) if STATE.exists() else {}
    python = None if docker else python_runtime()
    if docker:
        docker_command()
        configure_docker()
    else:
        configure_native()
    ready = setup_ready(saved, docker)
    if ready and not force:
        return
    print('Setting up TripRaft dependencies. Later starts reuse this setup.', flush=True)
    if not PNPM_SCRIPT.is_file():
        npm = shutil.which('npm')
        if not npm:
            raise RuntimeError('The Node.js installation must include npm.')
        npm_entry = Path(npm).parent / 'node_modules/npm/bin/npm-cli.js' if os.name == 'nt' else Path(npm).resolve()
        if not npm_entry.is_file():
            raise RuntimeError('Cannot find npm CLI. Repair the Node.js installation.')
        run([node, str(npm_entry), 'install', '--prefix', str(PNPM_HOME), '--no-audit', '--no-fund', '--ignore-scripts', f'pnpm@{PNPM_VERSION}'])
    env = child_env()
    # Replacing generated node_modules from an older store is safe and needs no TTY.
    run([node, str(PNPM_SCRIPT), 'install', '--frozen-lockfile'], env={**env, 'CI': 'true'})
    if not docker:
        if not venv_python().is_file():
            run([python, '-m', 'venv', str(VENV)])
        actual = run([str(venv_python()), '-c', 'import sys; print(sys.version_info[:2])'], capture=True)
        if actual != '(3, 11)':
            raise RuntimeError('Existing .venv uses another Python version. Preserve it elsewhere and rerun setup with Python 3.11.')
        run([str(venv_python()), '-m', 'pip', 'install', '--no-compile', '-r', str(API / 'requirements.txt'), '-r', str(API / 'requirements-dev.txt')], env=env)
    saved[mode] = fingerprint(docker)
    STATE.write_text(json.dumps(saved, indent=2) + '\n', encoding='utf-8')
    print('One-time setup complete.', flush=True)


def require_free_ports(ports):
    for port in ports:
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', port))
            except OSError as exc:
                raise RuntimeError(f'Port {port} is already in use. Stop its existing service before starting TripRaft.') from exc


def wait_ready(url, process, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError('A service exited during startup. See .tripraft/logs for details.')
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(.25)
    raise RuntimeError(f'Service did not become ready: {url}. See .tripraft/logs.')


def stop_child(process):
    """Stop only a process tree this launcher created, without touching unrelated services."""
    if process.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def start(node, docker, smoke, no_browser):
    env = child_env()
    require_free_ports([5173, 5174] + ([] if docker else [5000]))
    processes, logs = [], []
    compose = docker_command() if docker else None
    compose_started = False
    log_dir = LOCAL / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    def launch(name, command, cwd):
        log = (log_dir / f'{name}.log').open('w', encoding='utf-8')
        logs.append(log)
        options = {'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, **options)
        processes.append(process)
        return process

    try:
        if docker:
            # Refuse to take ownership of an existing Compose session.
            existing = run(compose + ['ps', '--status', 'running', '--quiet'], capture=True)
            if existing:
                raise RuntimeError('TripRaft Docker services are already running. Stop them before using this launcher.')
            compose_started = True
            run(compose + ['up', '--build', '--detach', '--wait', '--wait-timeout', '180'])
            wait_ready('http://127.0.0.1:5000/api/health/live', None)
        else:
            print('Applying database migrations; existing configuration is respected.', flush=True)
            run([str(venv_python()), '-m', 'alembic', 'upgrade', 'head'], cwd=API, env=env)
            api_process = launch('api', [str(venv_python()), str(API / 'run.py')], API)
            wait_ready('http://127.0.0.1:5000/api/health/live', api_process)
        for name, port in [('web', 5173), ('admin', 5174)]:
            app = ROOT / 'apps' / name
            process = launch(name, [node, str(app / 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--strictPort', '--port', str(port)], app)
            wait_ready(f'http://127.0.0.1:{port}', process)
        print('TripRaft is ready. Web: http://localhost:5173 | Admin: http://localhost:5174 | API: http://localhost:5000', flush=True)
        print('Press Ctrl+C to stop. Logs: .tripraft/logs', flush=True)
        if smoke:
            print('Startup smoke check passed; stopping owned services.', flush=True)
            return
        if not no_browser:
            webbrowser.open('http://localhost:5173')
        while True:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError('A project service stopped. See .tripraft/logs.')
            time.sleep(1)
    finally:
        for process in reversed(processes):
            stop_child(process)
        for log in logs:
            log.close()
        if compose_started:
            # Stop the launched services, retaining all database/catalog/upload volumes.
            run(compose + ['stop'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--setup', action='store_true', help='Install dependencies/configuration without starting services')
    action.add_argument('--check', action='store_true', help='Check prerequisites/setup status without installing or starting')
    action.add_argument('--smoke', action='store_true', help='Start all services, verify HTTP readiness, then stop')
    parser.add_argument('--docker', action='store_true', help='Use PostgreSQL, Redis, API and worker in Docker')
    parser.add_argument('--no-browser', action='store_true', help='Keep the browser closed')
    args = parser.parse_args()
    node = node_runtime()
    if args.check:
        docker_command() if args.docker else python_runtime()
        state = json.loads(STATE.read_text()) if STATE.is_file() else {}
        mode = 'docker' if args.docker else 'native'
        if not setup_ready(state, args.docker):
            raise RuntimeError('Setup is missing or dependencies changed. Run python start.py --setup first.')
        print('Prerequisites and saved setup are ready.')
        return
    setup(node, args.docker, force=args.setup)
    if not args.setup:
        start(node, args.docker, args.smoke, args.no_browser)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nTripRaft stopped.')
    except (RuntimeError, OSError, ValueError) as error:
        print(f'TripRaft: {error}', file=sys.stderr)
        sys.exit(1)
