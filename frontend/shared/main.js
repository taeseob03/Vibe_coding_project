import { mountAccount } from '/accounts/index.js';
import { mountOnboarding } from '/accounts/onboarding.js';
import { mountCharacter } from '/characters/index.js';
import { mountRecords } from '/records/index.js';

const user = await mountAccount();
if (user) {
  const profile = await mountOnboarding();
  if (profile) {
    document.querySelector('#character-section').hidden = false;
    document.querySelector('#record-section').hidden = false;
    await mountCharacter(profile.nickname);
    mountRecords();
  }
}
