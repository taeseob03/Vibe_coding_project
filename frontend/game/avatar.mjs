import { composeCharacter, DEPTS } from '/static/assets/character/pixel-character.js';
const colors = { green: 0x94cfa5, blue: 0x9ac8e8, yellow: 0xf1d67a, pink: 0xe8a9bf, purple: 0xb9a3de };

export function avatar(scene, person, stats, x, y, scale = 1) {
  const container = scene.add.container(x, y).setScale(scale);
  const shadow = scene.add.ellipse(0, 48, 82, 18, (colors[person.color] ?? colors.green), 0.3);
  const figure = scene.add.container(0, 0);
  const look = person.appearance || {base:'female',hair_length:'long',hair_color:'black'};
  const expression = person.state?.expression || 'neutral';
  const key = 'pixel-'+JSON.stringify([look,person.major||'computer',expression]);
  if(!scene.textures.exists(key)) {
    const texture=scene.textures.createCanvas(key,48,64),context=texture.context;
    const pixels=composeCharacter(look,person.major||'computer');
    pixels.forEach((pixel,index)=>{if(pixel){context.fillStyle=pixel;context.fillRect(index%48,Math.floor(index/48),1,1);}});
    if(expression==='focused') {
      context.strokeStyle='#222436';context.lineWidth=1;context.strokeRect(13.5,24.5,8,8);context.strokeRect(26.5,24.5,8,8);context.fillStyle='#222436';context.fillRect(21,27,6,1);
    } else if(['relaxed','energetic','heart_eyes'].includes(expression)) {
      for(const ex of [15,28]) {
        context.fillStyle='#ffe2c8';context.fillRect(ex,26,5,6);context.fillStyle=expression==='heart_eyes'?'#dc6380':'#302127';
        if(expression==='heart_eyes'){context.fillRect(ex,27,2,2);context.fillRect(ex+3,27,2,2);context.fillRect(ex+1,29,3,2);context.fillRect(ex+2,31,1,1);}
        else if(expression==='energetic'){context.fillRect(ex,28,1,1);context.fillRect(ex+1,27,3,1);context.fillRect(ex+4,28,1,1);}
        else context.fillRect(ex,29,5,1);
      }
    }
    texture.refresh();texture.setFilter(Phaser.Textures.FilterMode.NEAREST);
  }
  const body=scene.add.image(0,26,key).setOrigin(.5,.8).setScale(2);
  figure.add(body);
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
  if(person.grade && person.major) container.add(scene.add.text(0,person.title?106:87,`${person.grade}학년 · ${DEPTS[person.major]?.name||''}`,{fontFamily:'Campus Sans, sans-serif',fontSize:'9px',color:'#6d7c69'}).setOrigin(.5));
  return container;
}
