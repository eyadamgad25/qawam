import { describe, expect, it } from 'vitest';
import { PROJECT_NAME, isEducationalPrototype } from './placeholder';

describe('scaffold', () => {
  it('names the project', () => {
    expect(PROJECT_NAME).toBe('qawam');
  });

  it('stays an educational prototype flag', () => {
    expect(isEducationalPrototype()).toBe(true);
  });
});
