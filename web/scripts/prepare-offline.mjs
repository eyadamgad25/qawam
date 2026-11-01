// Copy the pose model and its WASM runtime into web/public so the coach runs
// with no internet (clinic interviews, demo rooms). Runs before `dev` and
// `build`. Never fails the build: without the files the app falls back to the
// public CDN, exactly as before.
import { copyFile, mkdir, readdir, stat, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const web = path.resolve(here, '..');
const repo = path.resolve(web, '..');
const require = createRequire(import.meta.url);

const MODEL_NAME = 'pose_landmarker_lite.task';
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/' +
  MODEL_NAME;

async function exists(file) {
  try {
    return (await stat(file)).size > 0;
  } catch {
    return false;
  }
}

async function copyWasm() {
  // package.json is not exported, so walk up from the resolved entry point
  let pkg = path.dirname(require.resolve('@mediapipe/tasks-vision'));
  while (path.basename(pkg) !== 'tasks-vision') pkg = path.dirname(pkg);
  const from = path.join(pkg, 'wasm');
  const to = path.join(web, 'public', 'mediapipe', 'wasm');
  await mkdir(to, { recursive: true });
  const files = await readdir(from);
  for (const file of files) await copyFile(path.join(from, file), path.join(to, file));
  return files.length;
}

async function prepareModel() {
  const to = path.join(web, 'public', 'models', MODEL_NAME);
  await mkdir(path.dirname(to), { recursive: true });
  if (await exists(to)) return 'already present';
  // The research pipeline keeps a copy here (git-ignored).
  for (const candidate of [
    path.join(repo, 'data', 'derived', 'models', MODEL_NAME),
    path.join(repo, 'data', 'derived', 'overlay', MODEL_NAME),
  ]) {
    if (await exists(candidate)) {
      await copyFile(candidate, to);
      return `copied from ${path.relative(repo, candidate)}`;
    }
  }
  const response = await fetch(MODEL_URL);
  if (!response.ok) throw new Error(`download failed: HTTP ${response.status}`);
  await writeFile(to, Buffer.from(await response.arrayBuffer()));
  return 'downloaded';
}

try {
  const n = await copyWasm();
  console.log(`[offline] pose runtime: ${n} files ready`);
} catch (error) {
  console.warn(`[offline] pose runtime not copied (${error.message}); the app will use the CDN`);
}
try {
  console.log(`[offline] pose model: ${await prepareModel()}`);
} catch (error) {
  console.warn(`[offline] pose model not available (${error.message}); the app will use the CDN`);
}
