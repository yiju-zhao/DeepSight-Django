// Flat ESLint config for ESLint v9+
// Note: TypeScript-specific linting is disabled here because
// @typescript-eslint packages are not installed in this repo.
// Type safety is enforced via `npm run type-check`.

import js from '@eslint/js';

export default [
  // Ignore build artifacts and TypeScript sources for linting
  { ignores: ['node_modules/**', 'dist/**', '**/*.ts', '**/*.tsx'] },

  // Apply recommended JS rules to any JS files that may exist
  {
    files: ['**/*.{js,jsx}'],
    ...js.configs.recommended,
  },
];

