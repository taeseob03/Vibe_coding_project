export async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      signal: options.signal ?? AbortSignal.timeout(12000),
      credentials: 'same-origin',
      headers: {
        ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...options.headers,
      },
    });
  } catch (error) {
    throw new Error(error.name === 'TimeoutError'
      ? '서버 응답이 늦어지고 있어요. 잠시 후 다시 시도해 주세요.'
      : '로컬 서버에 연결하지 못했어요. 서버 실행 상태를 확인해 주세요.');
  }
  if (response.status === 204) return null;
  const body = await response.json();
  if (!response.ok) {
    const error = new Error(body.error?.message ?? '요청에 실패했습니다.');
    error.status = response.status;
    throw error;
  }
  return body;
}
