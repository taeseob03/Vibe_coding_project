try {
  const [{ mountAccount }, { mountOnboarding }] = await Promise.all([
    import('/accounts/index.js?v=local-web-1'),
    import('/accounts/onboarding.js?v=local-web-1'),
  ]);
  const user = await mountAccount();
  if (user) {
    const profile = await mountOnboarding();
    if (profile) {
      const response = await fetch('/api/preview-status', { cache: 'no-store' });
      const preview = response.ok ? await response.json() : { enabled: false };
      if (preview.enabled) {
        window.location.replace('/app');
      } else {
        const [{ mountCharacter }, { mountRecords }] = await Promise.all([
          import('/characters/index.js?v=local-web-1'), import('/records/index.js?v=local-web-1'),
        ]);
        document.querySelector('#character-section').hidden = false;
        document.querySelector('#record-section').hidden = false;
        await mountCharacter(profile.nickname);
        mountRecords();
      }
    }
  }
} catch (error) {
  document.querySelector('#account').textContent = '화면을 불러오지 못했어요. Ctrl+F5로 새로고침하거나 아래 버튼으로 다시 시도해 주세요.';
  const retry = document.createElement('button');
  retry.textContent = '화면 다시 불러오기';
  retry.onclick = () => window.location.reload();
  document.querySelector('#account').after(retry);
  console.error('Account screen initialization failed:', error);
}
