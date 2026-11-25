import { access, copyFile, mkdir } from 'node:fs/promises';
import { join, resolve } from 'node:path';

const source = resolve('./entry.png');
const outputDir = resolve(process.env.MAKEFUN_OUTPUT_DIR ?? '/output');
const destination = join(outputDir, 'entry.png');

try {
  await access(source);
} catch {
  console.error(`Required input image is missing: ${source}`);
  process.exit(1);
}

try {
  await mkdir(outputDir, { recursive: true });
  await copyFile(source, destination);
  console.log(`Copied ${source} to ${destination}`);
} catch (error) {
  const detail = error instanceof Error ? error.message : String(error);
  console.error(`Unable to copy entry image to ${destination}: ${detail}`);
  process.exit(1);
}
