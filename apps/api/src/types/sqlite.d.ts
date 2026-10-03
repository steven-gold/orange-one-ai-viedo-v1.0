declare module 'node:sqlite' {
  export class DatabaseSync {
    constructor(path: string);
    prepare(sql: string): {
      all: (...params: unknown[]) => unknown[];
      run: (...params: unknown[]) => { changes?: number };
    };
    exec(sql: string): void;
    close(): void;
  }
}
