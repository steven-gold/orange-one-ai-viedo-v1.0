declare module '@neondatabase/serverless' {
  export function neon(connection: string): {
    query: (text: string, params?: unknown[]) => Promise<unknown>;
  };
}
