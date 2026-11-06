import { api } from '/shared/api.js';

export async function mountAccount() {
  const target = document.querySelector('#account');
  try {
    const user = await api('/auth/me');
    target.textContent = `로컬 개발용 사용자: ${user.id}`;
  } catch (error) {
    target.textContent = error.message;
  }
}
