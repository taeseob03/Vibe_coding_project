import { api } from '/shared/api.js';

export async function mountAccount() {
  const status = document.querySelector('#account');
  const form = document.querySelector('#login-form');
  const logout = document.querySelector('#logout');
  const button = form.querySelector('button');
  const input = form.querySelector('input');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    button.disabled = true;
    status.textContent = '접속 중…';
    try {
      await api('/auth/login', {
        method: 'POST', body: JSON.stringify({ username: input.value }),
      });
      window.location.reload();
    } catch (error) {
      status.textContent = error.message;
      button.disabled = false;
    }
  });
  logout.addEventListener('click', async () => {
    logout.disabled = true;
    try {
      await api('/auth/logout', { method: 'POST' });
      window.location.reload();
    } catch (error) {
      status.textContent = error.message;
      logout.disabled = false;
    }
  });
  try {
    const user = await api('/auth/me');
    status.textContent = user.auth_mode === 'id-only'
      ? `${user.username}님, 반가워요!`
      : '임시 개발 사용자로 접속 중입니다. 실제 접속은 DEV_AUTH_ENABLED=false로 전환하세요.';
    form.hidden = true;
    logout.hidden = user.auth_mode !== 'id-only';
    return user;
  } catch (error) {
    status.textContent = error.status === 401 ? '아이디를 입력해 시작하세요.' : error.message;
    form.hidden = false;
    return null;
  }
}
