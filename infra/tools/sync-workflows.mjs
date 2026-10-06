// Purpose: Copies canonical workflows into the .github/workflows paths GitHub discovers.
import { copyFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const root = new URL('../../', import.meta.url);
mkdirSync(fileURLToPath(new URL('.github/workflows/', root)), { recursive: true });
for (const name of ['ci.yml', 'deploy.yml']) {
  copyFileSync(new URL(`infra/github/workflows/${name}`, root), new URL(`.github/workflows/${name}`, root));
}
console.log('GitHub workflow discovery copies synchronized.');
