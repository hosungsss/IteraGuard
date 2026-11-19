const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const root=process.env.DMSG_TEST_ROOT || path.join(__dirname,'..');
const source=fs.readFileSync(path.join(root,'arena/web/main.js'),'utf8').split('function rememberSession')[0];
function run(response) {
  const context={document:{},fetch:async()=>response};vm.createContext(context);vm.runInContext(source,context);
  return vm.runInContext("api('/api/evaluate', {})",context);
}
test('expired website authentication is actionable even for HTML',async()=>{
  await assert.rejects(run({status:401,ok:false,json:async()=>{throw Error('html')}}),/다시 인증/);
});
test('busy model does not masquerade as a decision',async()=>{
  await assert.rejects(run({status:429,ok:false}),/다른 요청/);
});
test('login redirect HTML is not parsed as a decision',async()=>{
  await assert.rejects(run({status:200,ok:true,headers:{get:()=> 'text/html'}}),/JSON 대신/);
});
test('malformed JSON and arrays rejected',async()=>{
  await assert.rejects(run({ok:true,json:async()=>{throw Error('bad')}}),/응답 형식/);
  await assert.rejects(run({ok:true,json:async()=>[]}),/INVALID_API_RESPONSE/);
});
test('valid unavailable response remains unavailable',async()=>{
  const d=await run({ok:true,json:async()=>({mode:'MODEL_UNAVAILABLE'})});assert.equal(d.mode,'MODEL_UNAVAILABLE');
});
test('timeout warns to read saved state before retrying',async()=>{
  let expire,cleared=false;
  const context={document:{},AbortController,setTimeout:fn=>{expire=fn;return 1;},clearTimeout:()=>{cleared=true;},
    fetch:async(_,options)=>{expire();assert.ok(options.signal.aborted);throw {name:'AbortError'};}};
  vm.createContext(context);vm.runInContext(source,context);
  await assert.rejects(vm.runInContext("api('/api/evaluate', {})",context),/저장 상태를 먼저/);
  assert.ok(cleared);
});

function bootSignalHome(fetch) {
  function element(tagName) {
    const listeners = {};
    return {
      tagName, textContent: '', value: '', hidden: false, disabled: false, dataset: {}, attributes: {}, children: [],
      addEventListener(type, callback) { listeners[type] = callback; },
      setAttribute(name, value) { this.attributes[name] = value; },
      replaceChildren(...children) { this.children = children; },
      append(...children) { this.children.push(...children); },
      focus() {},
      trigger(type) { return (listeners[type] || this['on' + type])?.({preventDefault() {}}); }
    };
  }
  const elements = Object.fromEntries([
    'signalForm', 'text', 'run', 'inlineSignal', 'inlineSignalGrade', 'inlineSignalScores', 'inlineRequestedAction',
    'signalStatus', 'charCount', 'sampleNotice', 'signalExplanation', 'inlineConfirmation', 'inlineConfirmationText'
  ].map(id => {
    const node = element('div');
    node.hidden = ['inlineSignal', 'inlineSignalScores', 'inlineConfirmation'].includes(id);
    return [id, node];
  }));
  const document = {
    body: {dataset: {signalOnly: 'true'}},
    getElementById: id => elements[id],
    createElement: element
  };
  const context = vm.createContext({document, window: {}, fetch, AbortController, setTimeout, clearTimeout});
  for (const script of ['visual.js', 'signal.js']) {
    vm.runInContext(fs.readFileSync(path.join(root, 'arena/web', script), 'utf8'), context);
  }
  return elements;
}

function signalReply(status, body) {
  return {
    ok: status === 200, status,
    headers: {get: () => 'application/json'},
    json: async () => body
  };
}

test('the home form sends one request and shows its grade and requested action', async () => {
  const requests = [];
  const ui = bootSignalHome(async (url, config) => {
    requests.push([url, config.method, JSON.parse(config.body)]);
    return signalReply(200, {
      grade: 'red',
      requested_action: {id: 'share_auth_secret', label: '비밀번호·인증번호 알려주기'}
    });
  });
  assert.deepEqual(requests, []);
  const original = ' 가상 문자\n인증번호를 알려주세요. ';
  ui.text.value = original;
  ui.text.trigger('input');
  await ui.signalForm.trigger('submit');
  assert.deepEqual(requests, [['/api/signal', 'POST', {text: original, synthetic_only: true}]]);
  assert.equal(ui.inlineSignal.hidden, false);
  assert.equal(ui.inlineSignal.dataset.grade, 'red');
  assert.match(ui.inlineSignalGrade.textContent, /빨강/);
  assert.equal(ui.inlineRequestedAction.textContent, '비밀번호·인증번호 알려주기');
  assert.equal(ui.inlineSignalScores.hidden, true);
  ui.text.value = '다음 가상 문자';
  ui.text.trigger('input');
  assert.equal(ui.inlineSignal.hidden, true);
});

test('a failed signal request cannot leave the previous result visible', async () => {
  let response = signalReply(200, {
    grade: 'green',
    requested_action: {id: 'none', label: '요청 없음'}
  });
  const ui = bootSignalHome(async () => response);
  ui.text.value = '가상 일반 안내';
  await ui.signalForm.trigger('submit');
  assert.match(ui.inlineSignalGrade.textContent, /초록/);
  response = signalReply(503, {error: 'SIGNAL_MODEL_UNAVAILABLE'});
  await ui.signalForm.trigger('submit');
  assert.ok(ui.inlineSignal.hidden || !ui.inlineSignalGrade.textContent.includes('초록'));
  assert.equal(ui.run.disabled, false);
});

test('the confirmation excerpt uses original Unicode offsets and clears on input', async () => {
  const lead = ' 🧪 가상 안내\n';
  const clause = '인증번호를 알려주세요.';
  const start = Array.from(lead).length;
  const end = start + Array.from(clause).length;
  const ui = bootSignalHome(async () => signalReply(200, {
    grade: 'orange',
    requested_action: {id: 'share_auth_secret', label: '비밀번호·인증번호 알려주기'},
    scores: {red: .20, orange: .60, green: .05, gray: .15},
    confirmation_excerpt: {start, end}
  }));
  ui.text.value = lead + clause + ' ';
  await ui.signalForm.trigger('submit');
  assert.equal(ui.inlineConfirmation.hidden, false);
  assert.equal(ui.inlineConfirmationText.textContent, clause);
  assert.equal(ui.inlineSignalScores.hidden, false);
  ui.text.value = '다음 합성 안내';
  ui.text.trigger('input');
  assert.equal(ui.inlineConfirmation.hidden, true);
  assert.equal(ui.inlineConfirmationText.textContent, '');
});

test('green grade does not endorse a credential request', async () => {
  const ui = bootSignalHome(async () => signalReply(200, {
    grade: 'green', requested_action: {id: 'share_auth_secret', label: '비밀번호·인증번호 알려주기'}
  }));
  ui.text.value = '합성 예시'; await ui.signalForm.trigger('submit');
  assert.match(ui.signalStatus.textContent, /두 답이 엇갈립니다/);
  assert.match(ui.inlineRequestedAction.textContent, /인증번호/);
});
test('busy and unavailable have distinguishable messages', async () => {
  for (const [code, label, expected] of [[429,'MODEL_BUSY_RETRY_LATER',/다른 요청/],
                                          [503,'SIGNAL_MODEL_UNAVAILABLE',/로컬 모델/]]) {
    const ui = bootSignalHome(async () => signalReply(code, {error: label}));
    ui.text.value = '합성 예시'; await ui.signalForm.trigger('submit');
    assert.match(ui.signalStatus.textContent, expected);
    assert.equal(ui.inlineSignal.hidden, true);
  }
});

test('rounded near tie carries a caution without changing the observed grade', async () => {
  const ui = bootSignalHome(async () => signalReply(200, {grade:'green', scores:{green:.251,gray:.250,red:.250,orange:.249},
    requested_action:{id:'unknown',label:'불명확'}}));
  ui.text.value='합성'; await ui.signalForm.trigger('submit');
  assert.equal(ui.inlineSignal.dataset.grade,'green');
  assert.match(ui.signalStatus.textContent,/상위 두 선택 점수/);
});

test('link evidence control never submits on navigation or displays an obsolete reply', async () => {
  const listeners = {}, ids = {}, requests = [];
  const document = {getElementById: id => ids[id] ||= {value:'', checked:false,
    addEventListener: (event, fn) => {listeners[event] = fn;}}};
  let reply;
  const fetch = async (url, req) => { requests.push([url,JSON.parse(req.body)]);
    return new Promise(resolve => {reply = resolve;}); };
  vm.runInNewContext(fs.readFileSync(path.join(root, 'arena/web/link-review.js'), 'utf8'), {document,fetch});
  document.getElementById('message').value='합성 https://example.org/sample';
  document.getElementById('host').value=''; document.getElementById('second').checked=true;
  assert.equal(requests.length,0);
  const run=listeners.submit({preventDefault(){}});
  assert.equal(requests[0][0],'/api/link-review'); assert.equal(requests[0][1].share_host,'');
  listeners.input(); reply(signalReply(200,{observation:{status:'LISTED_EXACT',checked:1,matched:1},shadow_model:{status:'NOT_RUN'}}));
  await run;assert.equal(ids.output.textContent,'');assert.equal(ids.submitReview.disabled,false);
});


test('a reconciled grade keeps its explanation and does not reinterpret original scores', async () => {
  const explanation = '요청 행동이 불명확해 정상으로 확정하지 않습니다.';
  const ui = bootSignalHome(async () => signalReply(200, {
    grade: 'gray', requested_action: {id: 'unknown', label: '불명확'}, explanation,
    scores: {green: .251, gray: .250, red: .250, orange: .249},
    context_review: {adjusted: true, original: {grade: 'green'}}
  }));
  ui.text.value = '그 일 좀 해줘요.';
  await ui.signalForm.trigger('submit');
  assert.equal(ui.inlineSignal.dataset.grade, 'gray');
  assert.equal(ui.signalExplanation.textContent, explanation);
  assert.equal(ui.signalStatus.textContent, '');
  assert.match(ui.inlineSignalScores.children[2].textContent, /모델이 고른 등급은 초록/);
  const greenRow = ui.inlineSignalScores.children[1].children[2];
  assert.equal(greenRow.children[2].textContent, '25.1%');
});

test('the score card shows the four verified values to one decimal and clears on input', async () => {
  const ui = bootSignalHome(async () => signalReply(200, {
    grade: 'red', requested_action: {id: 'share_auth_secret', label: '인증정보 전달'},
    scores: {red: .718, orange: .092, green: .044, gray: .146}
  }));
  ui.text.value = '합성 예시';
  await ui.signalForm.trigger('submit');
  assert.equal(ui.inlineSignalScores.hidden, false);
  const list = ui.inlineSignalScores.children[1].children;
  assert.deepEqual(list.map(row => row.dataset.color), ['red', 'orange', 'green', 'gray']);
  assert.deepEqual(list.map(row => row.children[2].textContent), ['71.8%', '9.2%', '4.4%', '14.6%']);
  assert.equal(list[0].children[1].tagName, 'progress');
  assert.equal(list[0].children[1].attributes['aria-label'], '빨강 선택 점수');
  assert.equal(list[0].children[1].attributes.value, '0.718');
  ui.text.trigger('input');
  assert.equal(ui.inlineSignalScores.hidden, true);
  assert.equal(ui.inlineSignalScores.children.length, 0);
});

test('an out-of-range score set clears bars while preserving a valid result', async () => {
  const response = {grade: 'gray', requested_action: {id: 'unknown', label: '불명확'},
    scores: {red: .1, orange: .1, green: .2, gray: .6}};
  const ui = bootSignalHome(async () => signalReply(200, response));
  ui.text.value = '합성 예시';
  await ui.signalForm.trigger('submit');
  assert.equal(ui.inlineSignalScores.hidden, false);
  response.scores.gray = 1.6;
  await ui.signalForm.trigger('submit');
  assert.equal(ui.inlineSignalScores.hidden, true);
  assert.equal(ui.inlineSignalScores.children.length, 0);
  assert.equal(ui.inlineSignal.hidden, false);
  assert.equal(ui.inlineSignal.dataset.grade, 'gray');
});

{
  const { createHash, webcrypto } = require('node:crypto');
  const WEB = path.join(root, 'arena/web');
  const html = fs.readFileSync(path.join(WEB, 'signal.html'), 'utf8');
  const script = fs.readFileSync(path.join(WEB, 'signal.js'), 'utf8');
  const csv = Buffer.from('label,text\n0,synthetic example\n');

  function setup(crypto = webcrypto, { hostname, respond } = {}) {
    const handlers = {};
    const node = (id) => ({
      dataset: {},
      textContent: '',
      children: {},
      addEventListener(name, handler) { handlers[id + ':' + name] = handler; },
      querySelector(selector) { return this.children[selector] ||= node(id + ':' + selector); }
    });
    const nodes = Object.fromEntries([
      'text', 'signalForm', 'run', 'signalStatus', 'inlineSignal', 'inlineSignalGrade',
      'inlineRequestedAction', 'inlineSignalScores', 'charCount', 'openSignalBenchmark',
      'signalBenchmark', 'signalBenchmarkCsv', 'benchmarkCsvStatus', 'runSignalBenchmark',
      'benchmarkRunStatus', 'benchmarkResultMeta', 'benchmarkModelMeta', 'benchmarkNormal',
      'benchmarkPhishing', 'benchmarkRecall', 'benchmarkNormalRate', 'benchmarkStrict', 'benchmarkBinary'
    ].map((id) => [id, node(id)]));
    nodes.runSignalBenchmark.disabled = true;
    nodes.benchmarkRecall.querySelector('strong').textContent = '84.0%';
    nodes.benchmarkNormal.cells = Array.from({ length: 6 }, (_, i) => node('normal:' + i));
    nodes.benchmarkPhishing.cells = Array.from({ length: 6 }, (_, i) => node('phishing:' + i));
    const input = nodes.signalBenchmarkCsv;
    input.dataset.bytes = String(csv.length);
    input.dataset.sha256 = createHash('sha256').update(csv).digest('hex');
    const dialog = nodes.signalBenchmark;
    const opens = [];
    dialog.showModal = () => { dialog.open = true; opens.push(true); };
    const requests = [];
    const timers = new Map();
    let nextTimer = 0;
    const context = {
      document: { getElementById(id) { return nodes[id] || null; } },
      crypto,
      location: { hostname },
      async fetch(url, options) {
        requests.push([url, options.method, options.body, options.headers?.['Content-Type']]);
        assert.ok(respond, 'CSV verification and the public dialog must not make a network request');
        return respond();
      },
      setTimeout(handler, ms) {
        assert.equal(ms, 1500);
        timers.set(++nextTimer, handler);
        return nextTimer;
      },
      clearTimeout(id) { timers.delete(id); }
    };
    context.window = context;
    vm.runInNewContext(script, context);
    const choose = (file) => {
      input.files = file ? [file] : [];
      return handlers['signalBenchmarkCsv:change']();
    };
    const close = () => { dialog.open = false; return handlers['signalBenchmark:close'](); };
    return {
      nodes, opens, open: handlers['openSignalBenchmark:click'], close, choose,
      run: handlers['runSignalBenchmark:click'], requests, timers, status: nodes.benchmarkCsvStatus
    };
  }

  function fileFrom(bytes) {
    return { size: bytes.length, async arrayBuffer() { return Uint8Array.from(bytes).buffer; } };
  }

  test('benchmark dialog presents the fixed run and identifies its source CSV', () => {
    assert.match(html, /aria-haspopup="dialog" aria-controls="signalBenchmark">성능검증<\/button>/);
    assert.match(html, /<dialog id="signalBenchmark"[^>]* aria-labelledby="benchmarkTitle">/);
    assert.match(html, /2026-11-20 04:39 KST 재측정 결과/);
    assert.match(html, /<dt>정상 탐지율<\/dt><dd id="benchmarkNormalRate"><strong>84\.8%<\/strong> <span>\(425\/501\)<\/span>/);
    assert.match(html, /정상 문자 중 빨강·주황 경보가 없었던 비율로, 초록과 회색을 포함/);
    assert.match(html, /<th scope="row">정상<\/th><td>48<\/td><td>28<\/td><td>325<\/td><td>100<\/td><td>501<\/td>/);
    assert.match(html, /<th scope="row">피싱<\/th><td>18<\/td><td>24<\/td><td>3<\/td><td>5<\/td><td>50<\/td>/);
    assert.match(html, /blob\/438cfbb251410fee791f49d75d928520847030c3\/messenger_phishing_dataset\/kor\/test\.csv/);
    assert.match(html, /data-bytes="299076" data-sha256="31bed1a63581de43b1c81b84c8714873199ace1f92a4d93830478842df5443bf"/);
    assert.match(html, /<form method="dialog">/);
    const ui = setup();
    ui.open();
    ui.open();
    assert.equal(ui.opens.length, 1);
  });

  test('browser verification hashes local bytes and flags a same-size different file', async () => {
    const ui = setup();
    await ui.choose(fileFrom(csv));
    assert.equal(ui.status.dataset.state, 'match');
    const different = Buffer.from(csv);
    different[different.length - 2] = 65;
    await ui.choose(fileFrom(different));
    assert.equal(ui.status.dataset.state, 'mismatch');
    await ui.choose(null);
    assert.equal(ui.status.textContent, '');
  });

  test('a late hash cannot replace the status for a more recent file selection', async () => {
    const ui = setup();
    let resolve;
    const pending = ui.choose({
      size: csv.length,
      arrayBuffer() { return new Promise((done) => { resolve = done; }); }
    });
    await ui.choose({
      size: 1,
      arrayBuffer() { assert.fail('A different-size file should be rejected without reading it'); }
    });
    resolve(Uint8Array.from(csv).buffer);
    await pending;
    assert.equal(ui.status.dataset.state, 'mismatch');
  });

  const snapshot = (change = {}) => ({
    available: true, status: 'idle', completed: 0, total: 551, error: null, result: null, ...change
  });
  const measurement = {
    counts: { normal: { red: 6, orange: 4, green: 451, gray: 40 }, phishing: { red: 18, orange: 22, green: 5, gray: 5 } },
    finished_at: '2026-11-20T12:00:00Z', elapsed_ms: 3210, profile: 'high-recall'
  };
  const reply = (status, state) => ({ status, ok: status >= 200 && status < 300, json: async () => state });

  test('a local benchmark requests an empty JSON start and updates metrics only from a finished result', async () => {
    const responses = [
      reply(200, snapshot()),
      reply(202, snapshot({ status: 'running', completed: 7 })),
      reply(200, snapshot({ status: 'completed', completed: 551, result: measurement }))
    ];
    const ui = setup(webcrypto, { hostname: '127.0.0.1', respond: () => responses.shift() });
    await ui.open();
    assert.equal(ui.nodes.runSignalBenchmark.disabled, false);
    await ui.run();
    assert.deepEqual(ui.requests, [
      ['/api/signal/benchmark', 'GET', undefined, undefined],
      ['/api/signal/benchmark', 'POST', '{}', 'application/json']
    ]);
    assert.equal(ui.nodes.runSignalBenchmark.disabled, true);
    assert.match(ui.nodes.benchmarkRunStatus.textContent, /7\/551/);
    assert.equal(ui.nodes.benchmarkRecall.querySelector('strong').textContent, '84.0%');
    assert.equal(ui.timers.size, 1);
    await [...ui.timers.values()][0]();
    assert.equal(ui.timers.size, 0);
    assert.equal(ui.nodes.runSignalBenchmark.disabled, false);
    assert.equal(ui.nodes.benchmarkRecall.querySelector('strong').textContent, '80.0%');
    assert.equal(ui.nodes.benchmarkNormalRate.querySelector('strong').textContent, '98.0%');
    assert.equal(ui.nodes.benchmarkNormalRate.querySelector('span').textContent, '(491/501)');
    assert.equal(ui.nodes.benchmarkStrict.querySelector('span').textContent, '(491/551)');
    assert.equal(ui.nodes.benchmarkBinary.querySelector('span').textContent, '(531/551)');
    assert.equal(ui.nodes.benchmarkPhishing.cells[2].textContent, '22');
    assert.match(ui.nodes.benchmarkModelMeta.textContent, /high-recall.*3\.2초/);
  });

  test('reopening a running benchmark resynchronizes progress and a failure preserves its last complete result', async () => {
    const responses = [
      reply(200, snapshot({ status: 'running', completed: 7, result: measurement })),
      reply(200, snapshot({ status: 'running', completed: 25, result: measurement })),
      reply(200, snapshot({ status: 'failed', completed: 25, error: 'BENCHMARK_MODEL_UNAVAILABLE', result: measurement }))
    ];
    const ui = setup(webcrypto, { hostname: 'localhost', respond: () => responses.shift() });
    await ui.open();
    assert.equal(ui.nodes.benchmarkRecall.querySelector('strong').textContent, '80.0%');
    ui.close();
    assert.equal(ui.timers.size, 0);
    await ui.open();
    assert.match(ui.nodes.benchmarkRunStatus.textContent, /25\/551/);
    await [...ui.timers.values()][0]();
    assert.equal(ui.nodes.benchmarkRecall.querySelector('strong').textContent, '80.0%');
    assert.equal(ui.nodes.runSignalBenchmark.disabled, false);
    assert.match(ui.nodes.benchmarkRunStatus.textContent, /모델 연결 상태/);
  });

  test('public and unconfigured local views retain the saved benchmark with a disabled rerun', async () => {
    const publicView = setup(webcrypto, { hostname: 'arena.example' });
    await publicView.open();
    assert.equal(publicView.requests.length, 0);
    assert.equal(publicView.nodes.runSignalBenchmark.disabled, true);
    assert.match(html, /재측정은 로컬 Arena에서 실행할 수 있습니다/);
    const disabled = setup(webcrypto, {
      hostname: '127.0.0.1', respond: () => reply(404, { error: 'BENCHMARK_DISABLED' })
    });
    await disabled.open();
    assert.equal(disabled.nodes.runSignalBenchmark.disabled, true);
    assert.match(disabled.nodes.benchmarkRunStatus.textContent, /--signal-benchmark-csv/);
    assert.equal(disabled.nodes.benchmarkRecall.querySelector('strong').textContent, '84.0%');
  });

  test('a disconnected status check retries with GET and never starts a run automatically', async () => {
    let failed = false;
    const ui = setup(webcrypto, { hostname: 'localhost', respond: () => {
      if (!failed) {
        failed = true;
        throw new Error('disconnected');
      }
      return reply(200, snapshot());
    } });
    await ui.open();
    assert.match(ui.nodes.runSignalBenchmark.textContent, /상태 다시 확인/);
    await ui.run();
    assert.deepEqual(ui.requests.map(request => request[1]), ['GET', 'GET']);
    assert.equal(ui.nodes.runSignalBenchmark.textContent, '재측정 시작');
  });
}
