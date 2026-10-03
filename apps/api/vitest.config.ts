import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [
    {
      name: 'virtual-node-sqlite',
      enforce: 'pre',
      resolveId(id) {
        if (id === 'node:sqlite' || id === 'sqlite') {
          return '\0virtual-node-sqlite';
        }
        return null;
      },
      load(id) {
        if (id === '\0virtual-node-sqlite') {
          return [
            "import { createRequire } from 'node:module';",
            "const require = createRequire(import.meta.url);",
            "const sqlite = require('node:sqlite');",
            'export const DatabaseSync = sqlite.DatabaseSync;',
          ].join('\n');
        }
        return null;
      },
    },
  ],
  test: {
    environment: 'node',
    fileParallelism: false,
  },
});
