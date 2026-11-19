/* Display-only lexical clause context. No policy/model/network/storage calls.
 * Quotes and original_evidence are memory/display only; persist the separately
 * allowlisted evidence_display_trace. Lists locate context, never risk/pause.
 * CONFIG mirrors integration/v51_evidence.py; semantic/parity tests guard it.
 */
(function(root){
  'use strict';
  const SCHEMA_VERSION="dmsg-v51-evidence-display/1", MAX_TEXT=2000, MAX_CLAUSE=240;
  const CONFIG={"boundary":"[.!?。;]+(?=\\s|$)|[\\r\\n]+|\\s+(?:하지만|그런데|그러나|그리고|대신|but|however)\\s+","request":"(?:주세요|주시겠어요|주시겠습니까|주실래요|줄래요|줘요|해줘|해라|하라|하세요|하십시오|하셔야|바랍니다|해야\\s*(?:해|합)|보내세요|넘겨주세요|알려줘|설치해|눌러|클릭해|가져오세요|방문해)|(?:please|could you|would you)\\s","negation":"지\\s*(?:마|말)|(?:해서는|하면|해선)\\s*안|금지|(?:do not|never|don.t)\\s","warning":"경고|주의하세요|피싱\\s*예방","report":"라고\\s*(?:말했습니다|말했어요|말했다|했습니다|했어요|했다|들었습니다|들었어요|들었다|하더군요|하더라|전했습니다|전했어요|전했다)\\s*$|^(?:인용|교육\\s*자료|예시|신고\\s*(?:내용|문구))\\s*:|^(?:quoted|reported|example|training)\\s*:","uncertain_report":"예시|인용|라고|라는","context_heading":"^(?:(?:교육\\s*)?예시|인용|교육\\s*자료|경고|주의|신고\\s*(?:내용|문구)|example|training|quoted|reported)\\s*:","context_end":"^(?:예시|인용|교육\\s*자료)\\s*(?:끝|종료)(?:$|\\s|:)|^(?:예시|인용)는\\s*여기까지|^end of (?:example|quote)(?:$|\\s|:)","pairs":[["CREDENTIAL_TOPIC","인증\\s*번호|일회용\\s*(?:번호|비밀번호)|otp|비밀번호|패스워드|verification code|password","알려|보내|공유|전달|제공|입력|말하|말하지|주세요|주시겠|주실래|주지|send|share|enter|disclose"],["MONEY_TOPIC","송금|이체|입금|돈(?=$|\\s|[을이은])|금액|대금|계좌|[0-9]+\\s*(?:만\\s*원|천\\s*원|원)|money|payment","송금|이체|입금|보내|전송|주세요|주시겠|주지|transfer|send|wire"],["APPLICATION_TOPIC","원격|앱|프로그램|팀뷰어|애니데스크|remote|app","설치|실행|허용|접속|연결|install|allow|run"],["PERSONAL_DATA_TOPIC","주민등록번호|신분증|개인정보|카드번호|사진|personal data|identity document","알려|보내|공유|전달|제공|입력|주세요|주시겠|주실래|주지|send|share|enter|disclose"],["LINK_TOPIC","링크|url|https?://(?:(?!\\s|[<>]).)+|link","열|누르|눌러|클릭|접속|방문|open|click|visit"],["DISCLOSURE_TOPIC","가족|경찰|주변|다른\\s*사람|누구|family|police","말하|말하지|알리|신고|연락|이야기|tell|contact|report"],["ORDINARY_OBJECT_TOPIC","서류|자료|준비물|신발|우산|안내문|documents|umbrella","가져|준비|읽|착용|보내|주세요|주시겠|주지|bring|prepare|read|wear|send"]]};
  const clone=v=>JSON.parse(JSON.stringify(v));
  const cp=s=>Array.from(s);
  const cpIndex=(s,n)=>cp(s.slice(0,n)).length;
  const SPACE_PATTERN="[\\u0009-\\u000d\\u0020\\u0085\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]";
  const isSpace=c=>new RegExp('^'+SPACE_PATTERN+'$','u').test(c);
  const nonblank=s=>cp(s).some(c=>!isSpace(c));
  function matches(pattern,text){
    const r=new RegExp(pattern.replace(/\\s/g,SPACE_PATTERN),'giu'), out=[];let m;
    while((m=r.exec(text))!==null){
      out.push({start:cpIndex(text,m.index),end:cpIndex(text,m.index+m[0].length)});
      if(!m[0].length)r.lastIndex++;
    }return out;
  }
  function quoteRanges(text){
    const pairs={'"':'"',"'":"'",'“':'”','‘':'’','«':'»'};
    const chars=cp(text),stack=[],ranges=[];
    for(let i=0;i<chars.length;i++){
      const c=chars[i];
      if(c==="'"&&i&&i+1<chars.length&&/^[A-Za-z0-9]$/.test(chars[i-1])&&/^[A-Za-z0-9]$/.test(chars[i+1]))continue;
      if(stack.length&&c===stack[stack.length-1][1]){
        const start=stack.pop()[0];ranges.push([start,i+1,true]);
      }else if(Object.prototype.hasOwnProperty.call(pairs,c))stack.push([i,pairs[c]]);
    }
    stack.forEach(s=>ranges.push([s[0],chars.length,false]));return ranges;
  }
  function clauses(text){
    const chars=cp(text),out=[];let start=0;
    for(const m of matches(CONFIG.boundary,text).concat([null])){
      let end=m?m.start:chars.length;
      while(start<end&&isSpace(chars[start]))start++;
      while(end>start&&isSpace(chars[end-1]))end--;
      if(start<end)out.push([start,end]);
      if(m)start=m.end;
    }return out;
  }
  const inside=(s,e,ranges)=>ranges.some(([lo,hi,closed])=>closed&&lo<=s&&e<=hi);
  function inspect(chars,lo,hi,ranges,hasAnchor){
    const piece=chars.slice(lo,hi).join(''),topics=[],pairs=[],acts=[];
    for(const [name,tp,ap] of CONFIG.pairs){
      const ts=matches(tp,piece),vs=matches(ap,piece);
      if(ts.length)topics.push(name);
      if(ts.length&&vs.length){pairs.push(name);for(const m of ts.concat(vs))acts.push([lo+m.start,lo+m.end]);}
    }
    const request=matches(CONFIG.request,piece).length>0, negative=matches(CONFIG.negation,piece).length>0;
    const warning=matches(CONFIG.warning,piece).length>0, reported=matches(CONFIG.report,piece).length>0;
    const uncertainReport=matches(CONFIG.uncertain_report,piece).length>0;
    const eligible=!!(topics.length||request||hasAnchor);let mode='UNRESOLVED',reason=null;
    if(!eligible)return [false,mode,'NO_ACTION_CONTEXT_CANDIDATE',[]];
    if(hi-lo>MAX_CLAUSE)reason='CLAUSE_TOO_LONG_FOR_LOCAL_DISPLAY';
    else if(ranges.some(([s,e,closed])=>!closed&&s<hi&&lo<e))reason='UNBALANCED_QUOTATION';
    else if(!pairs.length)reason='NO_SUPPORTED_TOPIC_ACTION_PAIR';
    else{
      const quoted=acts.map(([s,e])=>inside(s,e,ranges));
      if(quoted.some(Boolean)&&!quoted.every(Boolean))reason='MIXED_QUOTED_AND_UNQUOTED_ACTION_CUES';
      else if(quoted.every(Boolean)||reported)mode='QUOTED_OR_REPORTED';
      else if(uncertainReport)reason='REPORT_SCOPE_UNRESOLVED';
      else if(negative&&request)reason='MIXED_NEGATED_AND_REQUEST_CUES';
      else if(negative)mode='NEGATED_OR_WARNING_CUE';
      else if(warning&&request)reason='WARNING_SCOPE_UNRESOLVED';
      else if(warning)mode='NEGATED_OR_WARNING_CUE';
      else if(request)mode='DIRECT_REQUEST_CUE';
      else reason='SPEECH_CONTEXT_UNRESOLVED';
    }return [eligible,mode,reason,pairs];
  }
  function enrichEvidence(text,result){
    if(typeof text!=='string'||cp(text).length>MAX_TEXT||!result||typeof result!=='object'||Array.isArray(result))throw new Error('INVALID_EVIDENCE_INPUT');
    const out=clone(result),chars=cp(text),previous=result.evidence_display;
    let original=previous&&previous.schema_version===SCHEMA_VERSION?result.original_evidence:result.evidence;
    if(original===undefined)original=[];
    const reasons=[];
    if(!Array.isArray(original)){original=[];reasons.push('INVALID_UPSTREAM_EVIDENCE_LIST');}
    out.original_evidence=clone(original);
    const cs=clauses(text),ranges=quoteRanges(text),anchors=cs.map(()=>[]),invalid=[];
    original.forEach((e,index)=>{
      const valid=!!(e&&typeof e==='object'&&!Array.isArray(e)&&Number.isInteger(e.start)&&Number.isInteger(e.end)&&0<=e.start&&e.start<e.end&&e.end<=chars.length&&typeof e.quote==='string'&&chars.slice(e.start,e.end).join('')===e.quote&&nonblank(e.quote));
      const match=cs.findIndex(([lo,hi])=>valid&&lo<=e.start&&e.start<e.end&&e.end<=hi);
      if(match<0)invalid.push(index);else anchors[match].push(index);
    });
    if(invalid.length)reasons.push('INVALID_OR_CROSS_CLAUSE_UPSTREAM_SPAN');
    const evidence=[],reviews=[],shown=[];let contextOpen=false;
    cs.forEach(([lo,hi],index)=>{
      let [eligible,mode,reason,pairs]=inspect(chars,lo,hi,ranges,anchors[index].length>0);
      const piece=chars.slice(lo,hi).join('');
      if(matches(CONFIG.context_end,piece).length)contextOpen=false;
      if(eligible&&contextOpen){mode='UNRESOLVED';reason='PRECEDING_CONTEXT_HEADING_SCOPE_UNRESOLVED';}
      if(matches(CONFIG.context_heading,piece).length)contextOpen=true;
      if(!eligible)return;
      const method=anchors[index].length?'UPSTREAM_ANCHOR_CLAUSE_CONTEXT':'LOCAL_TOPIC_ACTION_CLAUSE_CONTEXT';
      reviews.push({start:lo,end:hi,clause_mode:mode,status:reason?'UNAVAILABLE':'DISPLAYED',reason_code:reason,method,original_anchor_indexes:anchors[index]});
      if(reason){reasons.push(reason);return;}
      evidence.push({start:lo,end:hi,quote:chars.slice(lo,hi).join(''),kind:'TEXT_ACTION_CONTEXT',directness:mode,clause_mode:mode,origin:'LOCAL_DISPLAY_HEURISTIC',method,topic_cues:pairs,semantic_verified:false,original_anchor_indexes:anchors[index]});
      shown.push(...anchors[index]);
    });
    const n=reviews.length,unavailable=reviews.filter(r=>r.status==='UNAVAILABLE').length;
    if(!nonblank(text))reasons.push('EMPTY_TEXT');
    if(!evidence.length)reasons.push('NO_DISPLAYABLE_ACTION_CONTEXT');
    const status=evidence.length?(unavailable||invalid.length?'PARTIAL':'AVAILABLE'):(n||original.length||reasons[0]==='INVALID_UPSTREAM_EVIDENCE_LIST'?'UNAVAILABLE':'NOT_APPLICABLE');
    const meta={schema_version:SCHEMA_VERSION,status,source:'LOCAL_DISPLAY_HEURISTIC',extraction_method:'BOUNDED_TOPIC_ACTION_AND_SPEECH_CUES',offset_unit:'UNICODE_CODE_POINT',whitespace_contract:'EXPLICIT_UNICODE_WHITE_SPACE_NO_BOM',policy_changed:false,role:'DISPLAY_CONTEXT_NOT_DECISION_GROUNDING',semantic_verified:false,semantic_quality:'NOT_INDEPENDENTLY_EVALUATED',risk_classification:'NOT_PERFORMED',model_calls:0,reason_codes:Array.from(new Set(reasons)),candidate_clause_count:n,displayed_clause_count:evidence.length,unavailable_clause_count:unavailable,candidate_clause_coverage:n?evidence.length/n:null,unavailable_clause_rate:n?unavailable/n:null,coverage_denominator:'CLAUSES_WITH_TOPIC_OR_REQUEST_CUE_OR_VALID_UPSTREAM_ANCHOR',upstream_span_count:original.length,upstream_span_displayed_count:shown.length,upstream_span_unavailable_count:original.length-shown.length,upstream_span_unavailable_rate:original.length?(original.length-shown.length)/original.length:null,invalid_upstream_span_count:invalid.length,raw_text_persistence:'FORBIDDEN_DISPLAY_AND_ORIGINAL_EVIDENCE_MEMORY_ONLY'};
    out.evidence=evidence;out.evidence_display=meta;
    const safeKeys=['start','end','kind','clause_mode','origin','method','topic_cues','original_anchor_indexes'];
    out.evidence_display_trace=Object.assign({},clone(meta),{clauses:reviews,spans:evidence.map(e=>{const s={};safeKeys.forEach(k=>s[k]=clone(e[k]));return s;}),raw_text_stored:false});
    return out;
  }
  const api={enrichEvidence,SCHEMA_VERSION};
  if(typeof module==='object'&&module.exports)module.exports=api;
  root.DMSG_V51_EVIDENCE=api;
})(typeof globalThis!=='undefined'?globalThis:this);
