// The frontend needs no API secrets. Replace these paths with the agreed server contract.
export const config = {
  socialMode: 'demo', // 'server' uses authenticated HTTP endpoints; never silently falls back to demo.
  profileUrl: '/api/me',
  progressUrl: '/api/progress',
  postUrl: '/api/keywords',
  socialBase: '/api',
};
