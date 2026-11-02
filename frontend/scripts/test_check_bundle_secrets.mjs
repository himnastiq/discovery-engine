import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCRIPT_PATH = path.join(__dirname, 'check_bundle_secrets.mjs');

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'bundle-leak-test-'));

try {
  // Test 1: NEXT_PUBLIC_GEMINI leak
  fs.writeFileSync(
    path.join(tmpDir, 'chunk1.js'),
    'const key = process.env.NEXT_PUBLIC_GEMINI_API_KEY;'
  );
  let failed = false;
  try {
    execSync(`node "${SCRIPT_PATH}" "${tmpDir}"`, { stdio: 'pipe' });
  } catch {
    failed = true;
  }
  if (!failed) {
    throw new Error('Expected NEXT_PUBLIC_GEMINI leak to fail check_bundle_secrets!');
  }
  console.log('Positive control 1: Caught NEXT_PUBLIC_GEMINI leak.');

  // Test 2: AIza key pattern leak
  fs.writeFileSync(
    path.join(tmpDir, 'chunk1.js'),
    'const k = "AIzaSyB1234567890abcdefghijklmnopqrstuv";'
  );
  failed = false;
  try {
    execSync(`node "${SCRIPT_PATH}" "${tmpDir}"`, { stdio: 'pipe' });
  } catch {
    failed = true;
  }
  if (!failed) {
    throw new Error('Expected AIza pattern leak to fail check_bundle_secrets!');
  }
  console.log('Positive control 2: Caught AIza pattern leak.');

  // Test 3: GEMINI_API_KEY pattern leak
  fs.writeFileSync(
    path.join(tmpDir, 'chunk1.js'),
    'const GEMINI_API_KEY = "dummy-raw-token";'
  );
  failed = false;
  try {
    execSync(`node "${SCRIPT_PATH}" "${tmpDir}"`, { stdio: 'pipe' });
  } catch {
    failed = true;
  }
  if (!failed) {
    throw new Error('Expected GEMINI_API_KEY pattern leak to fail check_bundle_secrets!');
  }
  console.log('Positive control 3: Caught GEMINI_API_KEY pattern leak.');

  // Test 4: Clean chunk passes
  fs.writeFileSync(
    path.join(tmpDir, 'chunk1.js'),
    'console.log("Safe client code without secrets");'
  );
  execSync(`node "${SCRIPT_PATH}" "${tmpDir}"`, { stdio: 'pipe' });
  console.log('Negative control: Clean chunk passed.');
} finally {
  fs.rmSync(tmpDir, { recursive: true, force: true });
}

console.log('All positive and negative leak controls verified successfully.');
