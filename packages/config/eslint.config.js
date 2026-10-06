// Purpose: Applies the shared syntax/error lint rules to packages\config.
import tseslint from 'typescript-eslint';
export default [
  { ignores: ['dist/**', 'node_modules/**', 'src/generated/**'] },
  {
    files: ['**/*.{js,jsx,ts,tsx,cjs,mjs}'],
    languageOptions: { parser: tseslint.parser, parserOptions: { ecmaVersion: 'latest', sourceType: 'module', ecmaFeatures: { jsx: true } } },
    rules: { 'no-unreachable': 'error', 'no-dupe-keys': 'error', 'no-unsafe-finally': 'error', 'valid-typeof': 'error' }
  }
];
