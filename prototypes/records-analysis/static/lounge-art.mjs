// Canvas-native scenery and cached walking poses keep the lounge crisp at every size.
const rect = (ctx, color, x, y, w, h) => { ctx.fillStyle = color; ctx.fillRect(x, y, w, h); };

export function drawLoungeBackground(ctx) {
  rect(ctx, '#a9bd82', 0, 0, 900, 520);
  for (let y = 0; y < 520; y += 24) for (let x = 0; x < 900; x += 24) {
    if ((x / 24 + y / 24) % 2 === 0) rect(ctx, '#adc187', x, y, 24, 24);
    if ((x * 7 + y * 11) % 120 === 0) {
      rect(ctx, '#8fa96d', x + 6, y + 12, 3, 5);
      rect(ctx, '#bfd096', x + 10, y + 10, 3, 7);
    }
  }
  rect(ctx, '#b59b76', 36, 166, 828, 290);
  rect(ctx, '#e9d7b4', 42, 172, 816, 278);
  for (let y = 174; y < 450; y += 28) for (let x = 44; x < 856; x += 42) {
    rect(ctx, ((x + y) / 14) % 3 === 0 ? '#dfcaa6' : '#e4d0ae', x, y, 40, 26);
    rect(ctx, '#f2e3c7', x + 2, y + 2, 36, 2);
  }
  rect(ctx, '#d4bb92', 418, 122, 64, 50);
  rect(ctx, '#d4bb92', 418, 450, 64, 70);
  rect(ctx, '#8b6349', 328, 32, 244, 10);
  rect(ctx, '#ae6c4c', 340, 22, 220, 10);
  rect(ctx, '#d99767', 352, 16, 196, 6);
  rect(ctx, '#76513c', 340, 42, 220, 84);
  rect(ctx, '#f3e3c4', 346, 42, 208, 78);
  rect(ctx, '#ddc69f', 346, 80, 208, 6);
  for (const x of [360, 394, 480, 514]) {
    rect(ctx, '#786b58', x, 51, 24, 25);
    rect(ctx, '#91bac0', x + 3, 54, 18, 19);
    rect(ctx, '#d0e3dd', x + 4, 55, 6, 16);
    rect(ctx, '#b79e7a', x, 93, 24, 20);
  }
  rect(ctx, '#755d48', 432, 86, 36, 34);
  rect(ctx, '#7f9c9b', 436, 90, 28, 30);
  rect(ctx, '#ddc69f', 448, 90, 3, 30);
  rect(ctx, '#bca27c', 424, 120, 52, 6);
  rect(ctx, '#ead7b1', 416, 126, 68, 6);
  ctx.fillStyle = '#604936'; ctx.textAlign = 'center';
  ctx.font = 'bold 12px "Campus Pixel", monospace'; ctx.fillText('INU CAMPUS', 450, 64);
  function tree(x, y) {
    rect(ctx, '#8a9e6a', x - 18, y + 53, 44, 8);
    rect(ctx, '#70523b', x, y + 30, 10, 27);
    rect(ctx, '#9c7651', x + 2, y + 30, 4, 25);
    rect(ctx, '#45664a', x - 22, y + 14, 54, 28);
    rect(ctx, '#45664a', x - 14, y + 4, 38, 10);
    rect(ctx, '#658b56', x - 18, y + 12, 44, 24);
    rect(ctx, '#82a367', x - 10, y + 8, 25, 18);
    rect(ctx, '#75975f', x + 12, y + 24, 14, 12);
  }
  function bench(x, y) {
    rect(ctx, '#647255', x - 3, y + 31, 84, 7);
    rect(ctx, '#76513a', x + 7, y + 18, 6, 17);
    rect(ctx, '#76513a', x + 63, y + 18, 6, 17);
    rect(ctx, '#74523c', x, y, 78, 20);
    rect(ctx, '#c59260', x + 3, y + 3, 72, 6);
    rect(ctx, '#b17b50', x + 3, y + 12, 72, 6);
    rect(ctx, '#deb078', x - 4, y + 20, 86, 7);
    rect(ctx, '#8f6343', x - 4, y + 27, 86, 4);
  }
  for (const x of [62, 152, 738, 828]) tree(x, 42);
  bench(220, 105); bench(602, 105);
  for (const x of [70, 730]) {
    rect(ctx, '#775440', x, 474, 100, 30);
    rect(ctx, '#a57e56', x + 4, 478, 92, 22);
    for (let i = 0; i < 6; i++) {
      const fx = x + 10 + i * 15;
      rect(ctx, '#547343', fx, 467, 3, 17);
      rect(ctx, i % 2 ? '#d38276' : '#f2d37a', fx - 3, 461, 9, 9);
      rect(ctx, '#fff0bc', fx, 464, 3, 3);
    }
  }
  for (const x of [17, 871]) {
    rect(ctx, '#685d49', x, 179, 6, 58);
    rect(ctx, '#685d49', x - 5, 165, 16, 18);
    rect(ctx, '#f6dfa3', x - 2, 168, 10, 10);
    rect(ctx, '#8d7654', x - 5, 237, 16, 5);
  }
}

function placeholder(appearance) {
  const pixels = new Array(48 * 64).fill(null);
  const box = (x, y, w, h, c) => {
    for (let row = y; row < y + h; row++) for (let col = x; col < x + w; col++) pixels[row * 48 + col] = c;
  };
  box(13, 10, 22, 27, '#392f38'); box(16, 19, 16, 16, '#f3c19f');
  box(18, 24, 3, 3, '#332d32'); box(27, 24, 3, 3, '#332d32');
  box(13, 37, 22, 15, '#7998b8'); box(13, 39, 4, 11, '#f6efde'); box(31, 39, 4, 11, '#f6efde');
  box(17, 52, 6, 9, '#3c4660'); box(25, 52, 6, 9, '#3c4660');
  box(16, 59, 8, 3, '#382f35'); box(25, 59, 8, 3, '#382f35');
  if (appearance.hair_length === 'long') { box(11, 19, 4, 32, '#392f38'); box(33, 19, 4, 32, '#392f38'); }
  return pixels;
}

export function avatarFrames(compose, appearance, major, makeCanvas = () => document.createElement('canvas')) {
  const pixels = compose ? compose(appearance, major) : placeholder(appearance);
  return [0, 1, -1].map(phase => {
    const canvas = makeCanvas(); canvas.width = 48; canvas.height = 68;
    const ctx = canvas.getContext('2d');
    for (let y = 0; y < 64; y++) for (let x = 0; x < 48; x++) {
      const color = pixels[y * 48 + x]; if (!color) continue;
      let dy = 0;
      if (y >= 53 && x >= 14 && x <= 33) dy = x < 24 ? phase : -phase;
      if (y >= 40 && y <= 50 && ((x >= 12 && x <= 15) || (x >= 32 && x <= 35))) dy = x < 24 ? -phase : phase;
      rect(ctx, color, x, y + 2 + dy, 1, 1);
    }
    return canvas;
  });
}

export function walkingPose(moving, time, offset = 0) {
  return moving ? [0, 1, 0, 2][Math.floor(time * 8 + offset) % 4] : 0;
}
