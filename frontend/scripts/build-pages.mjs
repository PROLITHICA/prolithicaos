import { execFileSync } from 'node:child_process';
import { writeFileSync, copyFileSync } from 'node:fs';

const apiOrigin = (process.env.PROLITHICA_API_ORIGIN || '').replace(/\/$/, '');
if (apiOrigin) {
  const url = new URL(apiOrigin);
  if (url.protocol !== 'https:' || url.origin !== apiOrigin) throw new Error('PROLITHICA_API_ORIGIN must be an HTTPS origin without a path.');
}
execFileSync('npm', ['run', 'build', '--', '--base-href', '/prolithicaos/'], { stdio: 'inherit' });
const output = 'dist/frontend/browser';
writeFileSync(`${output}/deployment-config.js`, `window.PROLITHICA_CONFIG = ${JSON.stringify({ pages: true, apiOrigin })};\n`);
copyFileSync(`${output}/index.html`, `${output}/404.html`);
writeFileSync(`${output}/.nojekyll`, '');
