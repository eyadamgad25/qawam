import { describe, expect, it } from 'vitest';
import { API_NAME, roles } from './placeholder.js';

describe('scaffold', () => {
  it('names the api package', () => {
    expect(API_NAME).toBe('qawam-api');
  });

  it('lists the four product roles', () => {
    expect(roles()).toEqual(['patient', 'physio', 'clinic_admin', 'system_admin']);
  });
});
