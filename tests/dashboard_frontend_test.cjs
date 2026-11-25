const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('dashboard/index.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
class Element {
  constructor() { this.children=[]; this.style={}; this.listeners={}; this.disabled=false; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children=items; }
  setAttribute() {}
  addEventListener(type, fn) { this.listeners[type]=fn; }
}
const nodes = new Map();
const document = {
  querySelector(selector) {
    if (!nodes.has(selector)) nodes.set(selector, new Element());
    return nodes.get(selector);
  },
  createElement: () => new Element(),
  createElementNS: () => new Element(),
};
document.querySelector('meta[name="dashboard-token"]').content = 'test-token';
const state = {
  mode:'demo', status:'running', attached:true, reason:null,
  counts:{requests:2,success:2,failed:0,pages:1,topics_identified:2,topics_examined:1,topics_saved:0,messages_identified:4,messages_saved:3,active:0},
  last_request:null, safety:{state:'ready',delay_s:12}, controls:{pause:true,resume:false},
  size:{raw_bytes:0,processed_bytes:123,total_bytes:123}, events:[], timeline:[],
};
let fail = false, interval, posts = [], gets = [];
async function fetch(url, options) {
  if (fail) throw Error('offline');
  if (options && options.method === 'POST') { posts.push({url, options}); return {ok:true}; }
  if (url.startsWith('/api/records')) { gets.push(url); return {ok:true, json:async () => ({counts:{posts:1,replies:0,duplicates:0,rejected:null},latest:null,records:[{source:'synthetic',kind:'post',text:'synthetic content'}],has_more:true})}; }
  return {ok:true, json:async () => state};
}
const context = {document, fetch, setInterval: fn => {interval=fn;}, Date, Number, Math, String};
vm.runInNewContext(script, context);
async function tick() { await new Promise(resolve => setImmediate(resolve)); }
(async () => {
  await tick();
  assert.equal(nodes.get('#demo').style.display, 'block');
  assert.equal(nodes.get('#cards').children.length, 7);
  assert.equal(nodes.get('#charts').children.length, 3);
  assert.equal(nodes.get('#dataset-records').children.length, 1);
  assert.equal(nodes.get('#dataset-records').children[0].children[1].textContent, 'synthetic content');
  await nodes.get('#records-next').listeners.click();
  await tick();
  assert.ok(gets.includes('/api/records?offset=25'));
  assert.equal(nodes.get('#pause').disabled, false);
  await nodes.get('#pause').listeners.click();
  await tick();
  assert.equal(posts[0].url, '/api/pause');
  assert.equal(posts[0].options.headers['X-Dashboard-Token'], 'test-token');
  fail = true;
  await interval();
  assert.match(nodes.get('#connection').innerHTML, /Disconnected/);
  assert.equal(nodes.get('#pause').disabled, true);
  assert.equal(nodes.get('#resume').disabled, true);
  console.log('PASS frontend render, controls, polling and disconnected state');
})().catch(error => { console.error(error); process.exitCode = 1; });
