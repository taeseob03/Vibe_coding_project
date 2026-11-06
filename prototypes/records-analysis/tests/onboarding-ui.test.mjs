import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM, VirtualConsole } from 'jsdom';

test('actual onboarding selects and resumes department, gender and hair, including existing accounts', async () => {
  const html = await readFile(new URL('../../../frontend/index.html', import.meta.url), 'utf8');
  const renderer = await readFile(new URL('../../../frontend/assets/character/pixel-character.js', import.meta.url), 'utf8');
  const rendererUrl = `data:text/javascript;base64,${Buffer.from(renderer).toString('base64')}`;
  let source = await readFile(new URL('../../../frontend/accounts/onboarding.js', import.meta.url), 'utf8');
  source = source.replace(/import \{ api \} from '[^']+';/, 'const api = globalThis.__onboardApi;')
    .replace("'/assets/character/pixel-character.js'", JSON.stringify(rendererUrl));
  let profile = { nickname: '', step: 'nickname', onboarding_completed: false };
  const calls = [];
  globalThis.__onboardApi = async (path, options) => {
    if (!options) return structuredClone(profile);
    const body = JSON.parse(options.body); calls.push({ path, body });
    profile = { ...profile, ...body }; return profile;
  };
  const tick = () => new Promise(resolve => setTimeout(resolve, 10));
  const instances = [];
  async function mount(url, key) {
    const dom = new JSDOM(html, { url, virtualConsole: new VirtualConsole() }); instances.push(dom);
    globalThis.window = dom.window; globalThis.document = dom.window.document;
    globalThis.location = dom.window.location;
    const module = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}#${key}`);
    await module.mountOnboarding(); return dom.window.document;
  }
  function choose(doc, name, value) {
    const input = doc.querySelector(`input[name="${name}"][value="${value}"]`);
    input.checked = true; input.dispatchEvent(new window.Event('change'));
  }
  try {
    let doc = await mount('http://localhost/', 'new');
    doc.querySelector('#nickname').value = '픽셀친구';
    doc.querySelector('#setup-grade').value = '3';
    choose(doc, 'major', 'computer');
    doc.querySelector('#setup-next').click(); await tick();
    assert.equal(doc.querySelector('#color-step').hidden, false);
    choose(doc, 'base', 'male'); choose(doc, 'hair_length', 'short'); choose(doc, 'hair_color', 'blue');
    await tick();
    doc = await mount('http://localhost/', 'resume');
    assert.equal(doc.querySelector('input[name="base"]:checked').value, 'male');
    assert.equal(doc.querySelector('input[name="major"]:checked').value, 'computer');
    assert.equal(doc.querySelector('input[name="hair_color"]:checked').value, 'blue');
    assert.equal(doc.querySelector('#setup-grade').value, '3');
    doc.querySelector('#setup-form').dispatchEvent(new window.Event('submit', { cancelable: true }));
    await tick();
    assert.equal(calls.at(-1).path, '/profile/me/complete');
    assert.equal(calls.at(-1).body.appearance.hair_length, 'short');
    profile.onboarding_completed = true;
    doc = await mount('http://localhost/?customize=1', 'edit');
    assert.equal(doc.querySelector('#setup-form').hidden, false);
    assert.equal(doc.querySelector('#nickname').readOnly, true);
    choose(doc, 'hair_color', 'pink');
    doc.querySelector('#setup-form').dispatchEvent(new window.Event('submit', { cancelable: true }));
    await tick();
    assert.equal(calls.at(-1).path, '/profile/me/appearance');
    assert.equal(calls.at(-1).body.appearance.hair_color, 'pink');
    assert.ok(!Object.hasOwn(calls.at(-1).body, 'nickname'));
  } finally {
    for (const dom of instances) dom.window.close();
    delete globalThis.__onboardApi;
  }
});
