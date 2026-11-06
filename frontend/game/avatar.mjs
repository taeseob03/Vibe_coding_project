const colors = { green: 0x94cfa5, blue: 0x9ac8e8, yellow: 0xf1d67a, pink: 0xe8a9bf, purple: 0xb9a3de };

export function avatar(scene, person, stats, x, y, scale = 1) {
  const container = scene.add.container(x, y).setScale(scale);
  const shadow = scene.add.ellipse(0, 48, 82, 18, 0x2a3a32, 0.15);
  const figure = scene.add.container(0, 0);
  const body = scene.add.graphics();
  figure.add(body);
  body.fillStyle(colors[person.color] ?? colors.green).lineStyle(3, 0x314b40);
  body.fillRoundedRect(-37, -39, 74, 82, 29).strokeRoundedRect(-37, -39, 74, 82, 29);
  const expression = person.state?.expression || 'neutral';
  if (expression === 'relaxed') {
    body.lineStyle(2.5,0x314b40).lineBetween(-18,-6,-8,-3).lineBetween(8,-3,18,-6);
  } else if (expression === 'energetic') {
    body.lineStyle(2.5,0x314b40).beginPath().arc(-13,-3,5,Math.PI,Math.PI*2).strokePath();
    body.beginPath().arc(13,-3,5,Math.PI,Math.PI*2).strokePath();
  } else if (expression === 'heart_eyes') {
    for (const x of [-13,13]) figure.add(scene.add.text(x,-6,'♥',{fontFamily:'Campus Sans',fontSize:'15px',color:'#d86792'}).setOrigin(0.5));
  } else {
    body.fillStyle(0x314b40).fillEllipse(-13,-7,6,10).fillEllipse(13,-7,6,10);
  }
  if (expression === 'focused') {
    body.lineStyle(2,0x314b40).strokeRoundedRect(-24,-16,21,18,4).strokeRoundedRect(3,-16,21,18,4).lineBetween(-3,-8,3,-8);
    body.lineBetween(-6,14,6,14);
  } else {
    body.lineStyle(2.5,0x314b40).beginPath().arc(0,5,10,0,Math.PI).strokePath();
  }
  body.fillStyle(0xeb9caa, 0.65).fillEllipse(-25, 6, 11, 6).fillEllipse(25, 6, 11, 6);
  const active = stats.filter(item => item.count > 0);
  for (const item of active) {
    const size = 14 + item.level * 4;
    const g = scene.add.graphics();
    if (item.category === '공부') {
      g.fillStyle(0x456b97).lineStyle(2, 0x314b40).fillRoundedRect(24, 8, 28 + item.level * 2, 34, 3).strokeRoundedRect(24, 8, 28 + item.level * 2, 34, 3);
      g.lineStyle(2, 0xf6f2dc).lineBetween(31, 16, 47, 16).lineBetween(31, 23, 45, 23);
    } else if (item.category === '운동') {
      g.fillStyle(0x48576a).fillRect(-49, 17, 40, 7).fillRoundedRect(-51, 7, 10, 28, 3).fillRoundedRect(-18, 7, 10, 28, 3);
    } else if (item.category === '술') {
      g.fillStyle(0xe6af43).lineStyle(2, 0x7b683e).fillRoundedRect(-16, 32, 25, 24, 3).strokeRoundedRect(-16, 32, 25, 24, 3);
      g.fillStyle(0xfffbef).fillRoundedRect(-17, 29, 27, 9, 4);
    } else if (item.category === '연애') {
      const heart = scene.add.text(0, -65, '♥', { fontFamily: 'Campus Sans, sans-serif', fontSize: `${size + 12}px`, color: item.color }).setOrigin(0.5);
      figure.add(heart);
    }
    figure.add(g);
  }
  container.add([shadow, figure]);
  const name = scene.add.text(0, 66, person.nickname || '', { fontFamily: 'Campus Sans, sans-serif', fontSize: '15px', fontStyle: 'bold', color: '#314b40' }).setOrigin(0.5);
  container.add(name);
  if (person.title) container.add(scene.add.text(0, 87, person.title, { fontFamily: 'Campus Sans, sans-serif', fontSize: '11px', color: '#647766' }).setOrigin(0.5));
  scene.tweens.add({ targets: figure, y: -4, duration: 900, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
  return container;
}
