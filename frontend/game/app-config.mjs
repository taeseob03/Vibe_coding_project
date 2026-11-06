export const config = {
  socialMode: 'server',
  demoAnalysis: new URLSearchParams(location.search).get('mode') === 'demo',
};
