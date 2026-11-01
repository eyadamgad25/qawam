/**
 * Public surface of the Qawam API core. The Express layer (GP2) maps routes
 * onto these functions and Denied codes onto HTTP statuses; see
 * docs/architecture.md for the route table.
 */
export * from './domain/model.js';
export * from './domain/access.js';
export {
  validateSessionUpload,
  canonicalJson,
  contentHash,
} from './domain/validate.js';
export type { Validation } from './domain/validate.js';
export type { Store, Clock, Deps } from './store/ports.js';
export { MemoryStore } from './store/memory.js';
export { Denied, HTTP_STATUS } from './app/errors.js';
export type { DenyCode } from './app/errors.js';
export { ingestSessions, MAX_BATCH } from './app/sync.js';
export type { SyncResult, RejectReason } from './app/sync.js';
export {
  approveReference,
  prescribe,
  setConsent,
  patientSessions,
  reviewQueue,
} from './app/clinical.js';
export type { ReferenceInput, PrescriptionInput } from './app/clinical.js';
