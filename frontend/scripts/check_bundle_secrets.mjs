#!/usr/bin/env node
/**
 * Verification script (P8.2, Quality Gate R11).
 *
 * Inspects all client bundle JS chunks under .next/static/
 * and asserts that neither API_KEY nor RECOMMENDER_API_KEY
 * secrets appear in client-accessible assets.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_DIR = path.resolve(__dirname, '..');
const STATIC_DIR = path.join(FRONTEND_DIR, '.next', 'static');
const TARGET_DIR = process.argv[2] ? path.resolve(process.argv[2]) : STATIC_DIR;

if (!fs.existsSync(TARGET_DIR)) {
  console.error(`[ERROR] Static bundle directory not found at ${TARGET_DIR}. Run 'npm run build' first.`);
  process.exit(1);
}

function getAllFiles(dirPath, arrayOfFiles = []) {
  const files = fs.readdirSync(dirPath);
  for (const file of files) {
    const fullPath = path.join(dirPath, file);
    if (fs.statSync(fullPath).isDirectory()) {
      getAllFiles(fullPath, arrayOfFiles);
    } else if (file.endsWith('.js') || file.endsWith('.mjs')) {
      arrayOfFiles.push(fullPath);
    }
  }
  return arrayOfFiles;
}

const jsFiles = getAllFiles(TARGET_DIR);
console.log(`[INFO] Scanning ${jsFiles.length} client JavaScript chunks for secret leakages...`);

const geminiKeys = (process.env.GEMINI_API_KEYS || '')
  .split(',')
  .map(k => k.trim())
  .filter(k => k.length >= 8);

const testSecrets = [
  'TEST_SECRET_API_KEY_NEVER_LEAK',
  'super-secret-backend-key-12345',
  process.env.API_KEY,
  process.env.RECOMMENDER_API_KEY,
  ...geminiKeys,
].filter(Boolean);

const forbiddenPatterns = [
  { name: 'NEXT_PUBLIC_GEMINI prefix', regex: /NEXT_PUBLIC_GEMINI/i },
  { name: 'Google API Key pattern (AIza...)', regex: /AIza[0-9A-Za-z-_]{35}/ },
  { name: 'Gemini raw key or token pattern', regex: /GEMINI_API_KEY/i },
];

let leaksFound = 0;

for (const filePath of jsFiles) {
  const content = fs.readFileSync(filePath, 'utf-8');
  for (const secret of testSecrets) {
    if (secret && secret.length >= 8 && content.includes(secret)) {
      console.error(`[LEAK DETECTED] Secret "${secret}" found in client chunk: ${filePath}`);
      leaksFound++;
    }
  }
  for (const pattern of forbiddenPatterns) {
    if (pattern.regex.test(content)) {
      console.error(`[LEAK DETECTED] Forbidden pattern "${pattern.name}" matched in client chunk: ${filePath}`);
      leaksFound++;
    }
  }
}

if (leaksFound > 0) {
  console.error(`[FAILURE] Quality Gate R11 failed: ${leaksFound} secret occurrences found in client bundles.`);
  process.exit(1);
}

console.log('[SUCCESS] Quality Gate R11 passed: Zero server secrets leaked to client bundle.');
process.exit(0);

