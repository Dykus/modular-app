
/* colreorder-ui-v2: drag zagolovkov kolonok v liste; draggable perestavljaetsya
   posle kazhdoi pererisovki #shthead (MutationObserver), slushateli delegirovany
   na sam #shthead i perezhivajut innerHTML-zamenu. sheet.js NE izmenjaetsya. */
(function(){
"use strict";
var dragKey=null, overKey=null, before=true, bound=false;
function shthead(){return document.getElementById("shthead");}
function ths(){var t=shthead();if(!t)return[];var r=t.querySelector("tr.shcols");if(!r)return[];
 var out=[];for(var i=0;i<r.cells.length;i++){var th=r.cells[i];if(th.getAttribute("data-sort"))out.push(th);}return out;}
function keyOrder(){var a=ths(),o=[];for(var i=0;i<a.length;i++)o.push(a[i].getAttribute("data-sort"));return o;}
function equip(){var a=ths();for(var i=0;i<a.length;i++){a[i].setAttribute("draggable","true");a[i].classList.add("coldraggable");}}
function clearMarks(){var a=ths();for(var i=0;i<a.length;i++)a[i].classList.remove("colbefore","colafter");}
function reset(){dragKey=null;overKey=null;clearMarks();var a=ths();for(var i=0;i<a.length;i++)a[i].classList.remove("coldragging");}
function onDown(e){
 if(e.button!==0)return;
 var th=e.target.closest("th[data-sort]");if(!th)return;
 if(e.target.closest("input,select,button,a"))return;
 dragKey=th.getAttribute("data-sort");
 try{e.dataTransfer.effectAllowed="move";e.dataTransfer.setData("text/plain",dragKey);}catch(_){}
 th.classList.add("coldragging");
}
function onOver(e){
 if(!dragKey)return;e.preventDefault();
 var th=e.target.closest("th[data-sort]");if(!th)return;
 var k=th.getAttribute("data-sort");if(k===dragKey)return;
 var rc=th.getBoundingClientRect();before=e.clientX<rc.left+rc.width/2;
 clearMarks();th.classList.add(before?"colbefore":"colafter");overKey=k;
}
function onDrop(e){
 if(!dragKey)return;e.preventDefault();
 var order=keyOrder();
 var from=order.indexOf(dragKey);if(from<0){reset();return;}
 order.splice(from,1);
 var to=overKey?order.indexOf(overKey):order.length;
 if(to<0)to=order.length;
 if(!before)to+=1;
 order.splice(to,0,dragKey);
 var root=document.getElementById("shroot");
 var tid=root?root.getAttribute("data-tid"):"";
 reset();
 if(!tid){location.reload();return;}
 fetch("/tables/"+tid+"/cols/reorder",{method:"POST",
  headers:{"Content-Type":"application/json","X-Requested-With":"fetch"},
  body:JSON.stringify({keys:order})})
  .then(function(r){return r.json().then(function(j){return{st:r.status,j:j};});})
  .then(function(res){
   if(res.st===403){alert("Переставлять колонки может только роль с правом управления таблицей.");return;}
   if(res.j&&res.j.ok){location.reload();}else{alert("Не удалось сохранить порядок колонок.");}
  })
  .catch(function(){alert("Нет связи с сервером.");});
}
function bind(){
 var t=shthead();if(!t)return;
 if(bound)return;bound=true;
 t.addEventListener("dragstart",onDown);
 t.addEventListener("dragover",onOver);
 t.addEventListener("drop",onDrop);
 t.addEventListener("dragend",reset);
 equip();
 try{
  var mo=new MutationObserver(function(){equip();});
  mo.observe(t,{childList:true,subtree:true});
 }catch(_){
  setInterval(equip,1500); /* fallback, esli MutationObserver neprestupen */
 }
}
function start(){
 if(shthead()&&shthead().querySelector("tr.shcols")){bind();return;}
 var n=0,tm=setInterval(function(){n++;if(shthead()&&shthead().querySelector("tr.shcols")){clearInterval(tm);bind();}else if(n>20){clearInterval(tm);}},200);
}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",start);}else{start();}
})();
