import { describe, expect, it } from 'vitest';
import {
  LOCAL_MODEL_URL,
  LOCAL_WASM_URL,
  MODEL_URL,
  WASM_URL,
  looksLikeAsset,
  resolvePoseAssets,
} from './videoPose';

function reply(ok: boolean, type: string, length?: number) {
  const headers = new Headers({ 'content-type': type });
  if (length !== undefined) headers.set('content-length', String(length));
  return { ok, headers } as Response;
}

describe('offline pose assets', () => {
  it('rejects a dev server HTML fallback and a too-small model', () => {
    expect(looksLikeAsset(reply(true, 'text/html'))).toBe(false);
    expect(looksLikeAsset(reply(false, 'application/wasm'))).toBe(false);
    expect(
      looksLikeAsset(reply(true, 'application/octet-stream', 500), 1_000_000),
    ).toBe(false);
    expect(
      looksLikeAsset(reply(true, 'application/octet-stream', 5_777_746), 1_000_000),
    ).toBe(true);
  });

  it('uses the copies served by the app when both are present', async () => {
    const fetcher = (async (url: string) =>
      url.endsWith('.wasm')
        ? reply(true, 'application/wasm', 9_000_000)
        : reply(
            true,
            'application/octet-stream',
            5_777_746,
          )) as unknown as typeof fetch;
    expect(await resolvePoseAssets(fetcher)).toEqual({
      wasmUrl: LOCAL_WASM_URL,
      modelUrl: LOCAL_MODEL_URL,
      source: 'local',
    });
  });

  it('falls back to the CDN when the model was not copied or the request fails', async () => {
    const htmlFallback = (async () =>
      reply(true, 'text/html')) as unknown as typeof fetch;
    const failing = (async () => {
      throw new Error('offline');
    }) as unknown as typeof fetch;
    for (const fetcher of [htmlFallback, failing]) {
      expect(await resolvePoseAssets(fetcher)).toEqual({
        wasmUrl: WASM_URL,
        modelUrl: MODEL_URL,
        source: 'cdn',
      });
    }
  });
});
