/* Syntax and resource integrity gate; browser behavior is validated separately. */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.resolve(__dirname, '..');
let count = 0;
for (const name of fs.readdirSync(path.join(root, 'web'))) {
  if (!name.endsWith('.html')) continue;
  const file = path.join(root, 'web', name);
  const html = fs.readFileSync(file, 'utf8');
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
  const dup = ids.filter((id, index) => ids.indexOf(id) !== index);
  if (dup.length) throw new Error(name + ': duplicate ids ' + dup.join(', '));
  let index = 0;
  for (const match of html.matchAll(/<script(?![^>]*src)[^>]*>([\s\S]*?)<\/script>/g)) {
    new vm.Script(match[1], {filename: name + ':' + index++});
    count++;
  }
  for (const match of html.matchAll(/(?:src|href)="(\/static\/[^"?#]+)(?:[?#][^"]*)?"/g)) {
    // API/runtime assets are outside the static directory; static dependencies must exist.
    const target = path.join(root, 'web', match[1].slice('/static/'.length));
    if (!fs.existsSync(target)) throw new Error(name + ': missing resource ' + match[1]);
  }
}
for (const name of fs.readdirSync(path.join(root, 'web', 'assets'))) {
  if (!name.endsWith('.js')) continue;
  new vm.Script(fs.readFileSync(path.join(root, 'web', 'assets', name), 'utf8'), {filename:name});
  count++;
}
console.log('Web syntax and static resource integrity: ' + count + ' scripts passed');
