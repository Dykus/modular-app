
/* colwidth-ui-v1: širina kolonok v liste: primenjaet /widths i daet tjanut'
   pravuju granicu zagolovka (kak v Excel). sheet.js NE izmenjaetsya. */
(function(){
"use strict";
var W={}, KEYS=[], root=null, tid="", dragging=null;
function $(id){return document.getElementById(id);}
function px(v){return (parseInt(v,10)||0)+"px";}
function applyTh(){
 var ths=document.querySelectorAll("#shthead th[data-sort]");
 for(var i=0;i<ths.length;i++){
  var k=ths[i].getAttribute("data-sort"), w=W[k];
  var h=ths[i].querySelector(".cw-handle");
  if(w){ths[i].style.minWidth=px(w);ths[i].style.maxWidth=px(w);ths[i].style.width=px(w);}
  else{ths[i].style.minWidth="";ths[i].style.maxWidth="";ths[i].style.width="";}
  if(!h){h=document.createElement("span");h.className="cw-handle";h.setAttribute("data-key",k);
   h.title="Тяни, чтобы задать ширину; двойной клик — сбросить";ths[i].appendChild(h);}
 }
}
function applyTd(){
 var tds=document.querySelectorAll("#shtbody td[data-key]");
 for(var i=0;i<tds.length;i++){
  var k=tds[i].getAttribute("data-key"), w=W[k];
  if(w){tds[i].style.maxWidth=px(w);tds[i].style.overflow="hidden";
   tds[i].style.textOverflow="ellipsis";tds[i].style.whiteSpace="nowrap";}
  else{tds[i].style.maxWidth="";tds[i].style.overflow="";tds[i].style.textOverflow="";tds[i].style.whiteSpace="";}
 }
}
function apply(){applyTh();applyTd();}
function save(k,w){
 if(!tid)return;
 fetch("/tables/"+tid+"/width",{method:"POST",
  headers:{"Content-Type":"application/json","X-Requested-With":"fetch"},
  body:JSON.stringify({key:k,width:w})})
  .then(function(r){return r.json();})
  .then(function(j){if(j&&j.ok){W[k]=w>0?w:0;apply();}
   else if(j&&j.err==="badkey"){W[k]=0;apply();}})
  .catch(function(){});
}
function onDown(e){
 var h=e.target.closest(".cw-handle");if(!h)return;
 e.preventDefault();e.stopPropagation();
 var th=h.closest("th[data-sort]");if(!th)return;
 var k=th.getAttribute("data-sort");
 var start=e.clientX, base=parseInt(getComputedStyle(th).width,10)||W[k]||120;
 dragging={k:k,th:th,start:start,base:base,moved:false};
 th.classList.add("cw-resizing");
 document.body.style.cursor="col-resize";document.body.style.userSelect="none";
}
function onMove(e){
 if(!dragging)return;
 var dx=e.clientX-dragging.start;if(Math.abs(dx)>2)dragging.moved=true;
 var w=Math.max(40,Math.min(1200,dragging.base+dx));
 dragging.th.style.width=px(w);dragging.th.style.minWidth=px(w);dragging.th.style.maxWidth=px(w);
 var tds=document.querySelectorAll('#shtbody td[data-key="'+dragging.k+'"]');
 for(var i=0;i<tds.length;i++){tds[i].style.maxWidth=px(w);}
}
function onUp(){
 if(!dragging)return;
 var d=dragging;dragging=null;
 document.body.style.cursor="";document.body.style.userSelect="";
 if(d.th)d.th.classList.remove("cw-resizing");
 if(!d.moved)return;
 var w=parseInt(getComputedStyle(d.th).width,10)||0;
 save(d.k,w);
}
function onDbl(e){
 var h=e.target.closest(".cw-handle");if(!h)return;
 var th=h.closest("th[data-sort]");if(!th)return;
 var k=th.getAttribute("data-sort");
 th.style.width="";th.style.minWidth="";th.style.maxWidth="";
 save(k,0);
}
function bind(){
 root=$("shroot");if(!root)return;
 tid=root.getAttribute("data-tid")||"";
 var ht=$("shthead"), bd=$("shtbody");
 if(ht){ht.addEventListener("mousedown",onDown);ht.addEventListener("dblclick",onDbl);}
 if(bd){try{new MutationObserver(applyTd).observe(bd,{childList:true,subtree:true});}catch(_){setInterval(applyTd,1500);}}
 if(ht){try{new MutationObserver(applyTh).observe(ht,{childList:true,subtree:true});}catch(_){}}
 document.addEventListener("mousemove",onMove);
 document.addEventListener("mouseup",onUp);
}
function load(){
 if(!tid)return;
 fetch("/tables/"+tid+"/widths").then(function(r){return r.json();}).then(function(j){
  W=j.widths||{};KEYS=j.keys||[];apply();
 }).catch(function(){});
}
function start(){
 if(!$("shroot")){var n=0,tm=setInterval(function(){n++;if($("shroot")){clearInterval(tm);bind();load();}else if(n>20)clearInterval(tm);},200);return;}
 bind();load();
}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",start);}else{start();}
})();
