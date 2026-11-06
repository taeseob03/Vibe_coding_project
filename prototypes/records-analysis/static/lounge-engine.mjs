export const WIDTH = 900;
export const HEIGHT = 520;
const MARGIN = 55;

export function levelFor(count) {
  return count === 0 ? 0 : count < 5 ? 1 : count < 10 ? 2 : 3;
}

export function destination(random = Math.random) {
  return { x: MARGIN + random() * (WIDTH - MARGIN * 2), y: 150 + random() * (HEIGHT - 150 - 80) };
}

export function makeUsers(random = Math.random) {
  return [
    { id: 1, emoji: '🧑', counts: { '술': 0, '공부': 7, '연애': 5, '운동': 0 } },
    { id: 2, emoji: '👩', counts: { '술': 2, '공부': 0, '연애': 1, '운동': 10 } },
    { id: 3, emoji: '👨', counts: { '술': 5, '공부': 3, '연애': 10, '운동': 1 } },
  ].map(user => ({ ...user, ...destination(random), target: destination(random), speed: 40 + user.id * 9, wait: 0, moving: false, direction: 1 }));
}

export function step(user, elapsed, random = Math.random) {
  const dt = Math.min(Math.max(elapsed, 0), 0.05);
  if (user.wait > 0) {
    user.wait = Math.max(0, user.wait - dt);
    user.moving = false;
    return;
  }
  const dx = user.target.x - user.x;
  const dy = user.target.y - user.y;
  const distance = Math.hypot(dx, dy);
  if (distance <= user.speed * dt) {
    user.x = user.target.x;
    user.y = user.target.y;
    user.target = destination(random);
    user.wait = 0.6 + random() * 1.8;
    user.moving = false;
  } else {
    user.x += dx / distance * user.speed * dt;
    user.y += dy / distance * user.speed * dt;
    user.direction = dx < 0 ? -1 : 1;
    user.moving = true;
  }
}
