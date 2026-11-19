
/* formwidth-ui-v1: primenjaet glavnuju širinu kolonok v forme (serveryj HTML)
   po indeksu kolonki; rabotaet i na pervobytoj, i na dvuhstročnoj šapke. */
(function(){
"use strict";
function apply(W,KEYS){
 var tb=document.querySelector(".tscroll table");if(!tb)return;
 var thead=tb.tHead;if(!thead||!thead.rows.length)return;
 var hrow=thead.rows[thead.rows.length-1];
 var ths=hrow.cells;
 for(var i=0;i<KEYS.length&&i<ths.length;i++){
  var w=W[KEYS[i]];
  if(w){ths[i].style.minWidth=w+"px";ths[i].style.maxWidth=w+"px";ths[i].style.width=w+"px";}
 }
 var body=tb.tBodies[0];if(!body)return;
 for(var r=0;r<body.rows.length;r++){
  var tds=body.rows[r].cells;
  for(var j=0;j<KEYS.length&&j<tds.length;j++){
   var ww=W[KEYS[j]];
   if(ww){tds[j].style.maxWidth=ww+"px";tds[j].style.overflow="hidden";
    tds[j].style.textOverflow="ellipsis";tds[j].style.whiteSpace="nowrap";}
  }
 }
}
function run(){
 var m=location.pathname.match(/\/tables\/(\d+)/);if(!m)return;
 fetch("/tables/"+m[1]+"/widths").then(function(r){return r.json();}).then(function(j){
  apply(j.widths||{},j.keys||[]);
 }).catch(function(){});
}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",run);}else{run();}
})();
