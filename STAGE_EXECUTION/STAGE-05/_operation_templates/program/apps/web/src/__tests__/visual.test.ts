import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const css = readFileSync(resolve(import.meta.dirname, '../styles/shell.css'), 'utf8');

function token(name: string): string {
  const match = css.match(new RegExp(`${name}:\\s*([^;]+);`));
  if (!match) throw new Error(`missing css token ${name}`);
  return match[1].trim();
}

describe('shell visual geometry', () => {
  it('locks sidebar geometry tokens', () => {
    expect(token('--sidebar-expanded-width')).toBe('260px');
    expect(token('--sidebar-collapsed-width')).toBe('64px');
    expect(token('--shell-header-height')).toBe('56px');
  });

  it('keeps collapsed workspace scaling and reduced-motion contract', () => {
    expect(css).toContain('.shell--collapsed .shell-body');
    expect(css).toContain('grid-template-columns: var(--sidebar-collapsed-width) 1fr');
    expect(css).toContain("[data-reduced-motion='true']");
    expect(css).toContain('.nav-link--active');
  });
});
