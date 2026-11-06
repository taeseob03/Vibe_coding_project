import { mountAccount } from '/static/accounts/index.js';
import { mountOnboarding } from '/static/accounts/onboarding.js';
import { mountCharacter } from '/static/characters/index.js';
import { mountRecords } from '/static/records/index.js';

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
