import { mountAccount } from '/accounts/index.js';
import { mountOnboarding } from '/accounts/onboarding.js';
import { mountCharacter } from '/characters/index.js';
import { mountRecords } from '/records/index.js';

// main의 캐릭터 애니메이션 초안은 /characters/phaser-draft.js에 보존했습니다.
// Phaser 패키지/번들 환경 연결 전에는 로그인 진입점에서 import하지 않습니다.

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
