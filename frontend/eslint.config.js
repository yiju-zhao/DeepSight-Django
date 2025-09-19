// Flat ESLint config for ESLint v9+
// Minimal, strict ruleset: enable React Hooks rules for TS/TSX.
// We keep the ruleset intentionally small to avoid noisy warnings.

import js from '@eslint/js';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import tseslint from 'typescript-eslint';

export default [
  // Ignore build artifacts
  { ignores: ['node_modules/**', 'dist/**'] },

  // Base JS recommended for any JS files in the repo
  {
    files: ['**/*.{js,jsx}'],
    ...js.configs.recommended,
  },

  // TypeScript + React Hooks minimal config (strict)
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tseslint.parser,
    },
    plugins: {
      // Include TS plugin for parser support; rules kept minimal by design
      '@typescript-eslint': tseslint.plugin,
      react,
      'react-hooks': reactHooks,
    },
    rules: {
      // React core tweaks for modern React
      'react/react-in-jsx-scope': 'off',
      'react/prop-types': 'off',

      // Hooks rules (strict)
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'off',
    },
    settings: {
      react: { version: 'detect' },
    },
  },
];
