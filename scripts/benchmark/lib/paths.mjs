import { realpath } from 'node:fs/promises';
import { basename, dirname, isAbsolute, relative, resolve, sep } from 'node:path';

export async function resolveWithinRoot(root, target, label = 'path') {
  const rootReal = await realpath(root);
  let ancestor = resolve(target);
  const suffix = [];
  let physical;
  for (;;) {
    try {
      physical = await realpath(ancestor);
      break;
    } catch (error) {
      if (!['ENOENT', 'ENOTDIR'].includes(error.code)) throw error;
      const parent = dirname(ancestor);
      if (parent === ancestor) throw new Error(label + ' has no existing parent');
      suffix.unshift(basename(ancestor));
      ancestor = parent;
    }
  }
  const candidate = resolve(physical, ...suffix);
  const rel = relative(rootReal, candidate);
  if (rel === '..' || rel.startsWith('..' + sep) || isAbsolute(rel)) throw new Error(label + ' must resolve inside Test Server');
  return candidate;
}
