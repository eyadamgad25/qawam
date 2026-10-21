import eslint from '@eslint/js';
import { defineConfig } from 'eslint/config';
import prettier from 'eslint-config-prettier';
import tseslint from 'typescript-eslint';

export default defineConfig(
  {
    ignores: ['**/dist/**', '**/node_modules/**', '**/coverage/**'],
  },
  eslint.configs.recommended,
  tseslint.configs.recommended,
  prettier,
  {
    files: ['web/src/**/*.ts', 'web/src/**/*.tsx', 'api/src/**/*.ts'],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      eqeqeq: ['error', 'always'],
      'no-console': 'off',
    },
  },
);
