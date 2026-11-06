import { avatar } from './avatar.mjs';
export function createLounge(canvas) {
  const host = document.createElement('div');
  host.id = 'live-lounge';
  host.setAttribute('aria-label','라운지 캐릭터');
  canvas.replaceWith(host);
  let roomId, socket, reconnect, closed = false, scene, pendingPeople = [];
  const actors = new Map();
  class LoungeScene extends Phaser.Scene {
    create() {
      scene = this;
      this.add.rectangle(450,260,900,520,0xe7eedf);
      this.add.rectangle(450,290,900,72,0xd9cbb3);
      this.add.rectangle(450,310,72,420,0xd9cbb3);
      this.add.rectangle(450,80,220,105,0x9cae91).setStrokeStyle(3,0x6a8064);
      this.add.triangle(450,14,-125,35,0,-35,125,35,0x72876b);
      this.add.text(450,78,'CAMPUS',{fontFamily:'sans-serif',fontSize:'22px',color:'#fff9e9'}).setOrigin(0.5);
      for (const x of [70,830]) {
        this.add.rectangle(x,140,16,65,0x9b805d);
        this.add.circle(x,100,44,0x9bb68d);
        this.add.circle(x-24,111,26,0xabc29b);
      }
      apply(pendingPeople);
    }
  }
  const game = new Phaser.Game({ type: Phaser.CANVAS, width:900,height:520,parent:host,backgroundColor:'#e7eedf',
    scene:LoungeScene,audio:{noAudio:true},fps:{target:30},banner:false,
    scale:{mode:Phaser.Scale.FIT,autoCenter:Phaser.Scale.CENTER_BOTH} });
  function apply(people) {
    pendingPeople = people;
    if (!scene) return;
    const present = new Set(people.map(person => person.id));
    for (const [id, actor] of actors) if (!present.has(id)) { actor.container.destroy(); actors.delete(id); }
    for (const person of people) {
      const stats = person.stats || Object.entries(person.counts || {}).map(([category,count]) => ({category,count,level:count===0?0:count<5?1:count<10?2:3,color:'#ec4899'}));
      const signature = JSON.stringify([stats,person.color,person.title,person.nickname,person.state]);
      let actor = actors.get(person.id);
      if (!actor || actor.signature !== signature) {
        actor?.container.destroy();
        const container = avatar(scene,person,stats,person.x ?? 450,person.y ?? 270,0.74);
        actor = { container,signature }; actors.set(person.id,actor);
      }
      if (person.x !== undefined) {
        scene.tweens.killTweensOf(actor.container);
        scene.tweens.add({targets:actor.container,x:person.x,y:person.y,duration:110});
      }
      actor.container.setDepth(person.y || 200);
    }
    host.setAttribute('aria-label', people.map(person => person.nickname).join(', ')+'의 공유 라운지');
  }
  function connect() {
    if (closed || !roomId) return;
    clearTimeout(reconnect);
    const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:';
    socket = new WebSocket(`${scheme}//${location.host}/api/lounges/${roomId}/live`);
    socket.onmessage = event => {
      const frame = JSON.parse(event.data);
      if (frame.type === 'snapshot') {
        apply(frame.people);
        document.querySelector('#live-status').textContent = `실시간 연결 · 접속 ${frame.people.filter(person=>person.online).length}명`;
      }
    };
    socket.onclose = event => {
      document.querySelector('#live-status').textContent = event.code === 1008 ? '접속 권한이 만료됐어요. 다시 접속해 주세요.' : '연결을 다시 시도하고 있어요…';
      if (!closed && event.code !== 1008) reconnect = setTimeout(connect,1500);
    };
  }
  return {
    setPeople(people) { if (!socket || socket.readyState !== WebSocket.OPEN) apply(people); },
    setRoom(id) {
      if (roomId === id) return;
      if (socket) { socket.onclose=null;socket.close(); }
      clearTimeout(reconnect);roomId=id;actors.forEach(actor=>actor.container.destroy());actors.clear();
      if (id) connect();
    },
    destroy() {closed=true;clearTimeout(reconnect);socket?.close();game.destroy(true);},
  };
}
