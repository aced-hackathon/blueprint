"use strict";
// Deliberately no fetch, XHR, WebSocket, storage, analytics, model runtime or bank API.
const messages=document.getElementById('messages');
const input=document.getElementById('private-input');
const opening=messages.innerHTML;
function append(text,role){
  const el=document.createElement('div');el.className='message '+role;
  const label=document.createElement('div');label.className='message-label';label.textContent=role==='user'?'FICTIONAL MESSAGE':'SCRIPTED EXAMPLE';
  const body=document.createElement('div');body.textContent=text;
  el.append(label,body);messages.append(el);messages.scrollTop=messages.scrollHeight;
}
document.getElementById('send').onclick=()=>{
  const text=input.value.trim();if(!text)return;
  append(text,'user');input.value='';
  append('You can keep your reasons separate from your banking plan. This fixed demonstration reply does not analyze what you wrote. If you want help preparing a deposit, review the optional statement alongside this conversation.','assistant');
};
document.getElementById('sample').onclick=()=>{input.value='Fictional example: I want to move because a difficult family situation makes me want more personal space. I do not want this reason in my banking profile.';input.focus();};
document.getElementById('clear').onclick=()=>{messages.innerHTML=opening;input.value='';document.getElementById('consent').checked=false;document.getElementById('share').disabled=true;};
document.getElementById('consent').onchange=event=>document.getElementById('share').disabled=!event.target.checked;
document.getElementById('share').onclick=()=>{
  if(!document.getElementById('consent').checked)return;
  // Opaque-origin sandbox: explicit enum only. No transcript extraction or summarization.
  parent.postMessage({type:'APPROVE_MOVING_GOAL'},'*');
};
