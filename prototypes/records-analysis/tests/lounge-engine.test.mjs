import test from 'node:test';
import assert from 'node:assert/strict';
import { makeUsers, step, levelFor, WIDTH, HEIGHT } from '../static/lounge-engine.mjs';

test('three users move and remain inside the room during a long simulation',()=>{
  let seed=7;
  const random=()=>{seed=(seed*16807)%2147483647;return (seed-1)/2147483646;};
  const users=makeUsers(random);
  assert.deepEqual(users.map(u=>u.id),[1,2,3]);
  const starts=users.map(u=>[u.x,u.y]);
  for(let i=0;i<36000;i++) for(const user of users){
    step(user,1/60,random);
    assert.ok(user.x>=55 && user.x<=WIDTH-55 && user.y>=150 && user.y<=HEIGHT-55);
  }
  users.forEach((u,i)=>assert.ok(Math.hypot(u.x-starts[i][0],u.y-starts[i][1])>1));
});
test('arrivals pause, and large frame gaps do not teleport a character',()=>{
  const u=makeUsers(()=>.5)[0];u.target={x:u.x+1,y:u.y};step(u,.05,()=>.5);
  assert.ok(u.wait>0);const x=u.x;step(u,.05);assert.equal(u.x,x);
  u.wait=0;u.target={x:800,y:400};const before={x:u.x,y:u.y};step(u,100);
  assert.ok(Math.hypot(u.x-before.x,u.y-before.y)<=u.speed*.05+.0001);
});
test('growth boundaries match record effects',()=>{
  assert.deepEqual([0,1,4,5,9,10,100].map(levelFor),[0,1,1,2,2,3,3]);
});
