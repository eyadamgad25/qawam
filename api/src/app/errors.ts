/** A refused request. `code` maps to an HTTP status in the Express layer. */
export type DenyCode = 'NOT_FOUND' | 'FORBIDDEN' | 'INVALID' | 'CONFLICT';

export class Denied extends Error {
  constructor(
    readonly code: DenyCode,
    message: string,
  ) {
    super(message);
    this.name = 'Denied';
  }
}

export const HTTP_STATUS: Readonly<Record<DenyCode, number>> = {
  NOT_FOUND: 404,
  FORBIDDEN: 403,
  INVALID: 422,
  CONFLICT: 409,
};
