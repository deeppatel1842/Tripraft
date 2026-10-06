// Purpose: Provides babel.config logic and exports for apps\admin.
module.exports = {
  env: { test: { plugins: [require('./tests/viteEnvTransform.cjs')] } },
  presets: [ ['@babel/preset-env', { targets: { node: 'current' } }], ['@babel/preset-react', { runtime: 'automatic' }], '@babel/preset-typescript' ],
};
