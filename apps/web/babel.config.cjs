// Purpose: Provides babel.config logic and exports for apps\web.
module.exports = {
  env: { test: { plugins: [require('./tests/viteEnvTransform.cjs')] } },
  presets: [
    ['@babel/preset-env', { targets: { node: 'current' } }],
    ['@babel/preset-react', { runtime: 'automatic' }],
  ],
};
