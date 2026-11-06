export async function api(path, options = {}) {
  // A: 실제 인증을 구현할 때 토큰/쿠키 전달을 이곳에 연결합니다.
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error?.message ?? '요청에 실패했습니다.');
  return body;
}
