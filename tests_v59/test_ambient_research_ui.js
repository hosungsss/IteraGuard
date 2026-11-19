'use strict';
// No browser provider, network, GPU, paid API or model inference.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const ROOT = path.resolve(__dirname, '..');

function ambient({ reduced=false, hidden=false } = {}) {
  const frames=[]; const listeners={}; const ops=[];
  const ctx={
    setTransform(){},clearRect(){ops.push('clear');}, beginPath(){}, arc(){},fill(){},stroke(){},
    moveTo(){},lineTo(){}, createRadialGradient(){return {addColorStop(){}};},
    set lineWidth(v){},set strokeStyle(v){},set fillStyle(v){}
  };
  const canvas={width:0,height:0,style:{},getContext:(type)=>type==='2d'?ctx:null};
  const context={
    document:{hidden,getElementById:id=>id==='ambient3d'?canvas:null,addEventListener(name,cb){listeners[name]=cb;}},
    window:{innerWidth:900,innerHeight:700,devicePixelRatio:1,matchMedia:()=>({matches:reduced}),requestAnimationFrame(cb){frames.push(cb);},addEventListener(){}},
    console
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(ROOT,'arena/web/ambient3d.js'),'utf8'),context);
  return {canvas,frames,listeners,ops,context};
}

test('ambient 3D uses bounded deferred animation; never calls remote APIs',()=>{
  const a=ambient();assert.equal(a.frames.length,1);
  a.frames.shift()(100);
  assert.ok(a.ops.includes('clear'));
  assert.ok(a.canvas.width<=2400*1.5);
  assert.equal(a.frames.length,1);
});

test('reduced motion performs one static drawing and does not schedule loop',()=>{
  const a=ambient({reduced:true});
  assert.equal(a.frames.length,0);assert.ok(a.ops.includes('clear'));
});

test('hidden document never starts the 3D animation',()=>{
  const a=ambient({hidden:true});assert.equal(a.frames.length,0);
});

test('source-bound reference samples only change the editor and send no model call',()=>{
  const handlers={},examples={};
  for(const key of ['delivery','wedding','card','invoice','toll','safety'])examples[key]={
    dataset:{research:key},addEventListener(name,fn){handlers[key]=fn;}
  };
  let inputEvents=0,focused=0;
  const text={disabled:false,value:'',dispatchEvent(ev){inputEvents+=1;assert.equal(ev.type,'input');},focus(){focused+=1;}};
  const note={textContent:''};
  const context={document:{
    getElementById:id=>id==='text'?text:id==='researchNotice'?note:null,
    querySelectorAll:()=>Object.values(examples)
  },Event:class Event{constructor(type){this.type=type;}},console};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(ROOT,'arena/web/research.js'),'utf8'),context);
  handlers.invoice();
  assert.match(text.value,/계좌/);
  assert.equal(inputEvents,1);assert.equal(focused,1);
  assert.match(note.textContent,/재구성 합성 문장/);
});

test('case UI contains no executable URLs, auto bank transfer or fake model mode',()=>{
  const html=fs.readFileSync(path.join(ROOT,'arena/web/index.html'),'utf8');
  assert.match(html,/data-research="invoice"/);
  assert.match(html,/id="jevConsent"/);
  assert.match(html,/id="ambient3d"/);
  const js=fs.readFileSync(path.join(ROOT,'arena/web/research.js'),'utf8');
  assert.doesNotMatch(js,/fetch\(/);
  assert.doesNotMatch(js,/localStorage/);
  assert.doesNotMatch(js,/api\/evaluate/);
});
