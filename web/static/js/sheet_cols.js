
/* colreorder-ui-v1: peretaskivanie zagolovkov kolonok v liste (otdel'no ot sheet.js) */
(function(){
var dragKey=null, overKey=null, before=true;
function ths(){var out=[];var t=document.getElementById("shthead");if(!t)return out;
 var r=t.querySelector("tr.shcols");if(!r)return out;
 for(var i=0;i<r.cells.length;i++){var th=r.cells[i];var k=th.getAttribute("data-sort");if(k)out.push(th);}
 return out;}
function keyOrder(){var a=ths(),o=[];for(var i=0;i<a.length;i++)o.push(a[i].getAttribute("data-sort"));return o;}
function clearMarks(){var a=ths();for(var i=0;i<a.length;i++){a[i].classList.remove("colbefore","colafter");}}
function onDown(e){
 if(e.button!==0)return;
 var th=e.target.closest("th[data-sort]");if(!th)return;
 if(e.target.closest("input,select,button"))return;
 dragKey=th.getAttribute("data-sort");
 try{e.dataTransfer.setDragImage(th,8,8);}catch(_){}
 e.dataTransfer.effectAllowed="move";
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
 var tidEl=document.getElementById("shroot");
 var tid=tidEl?tidEl.getAttribute("data-tid"):"";
 reset();
 if(!tid){location.reload();return;}
 fetch("/tables/"+tid+"/cols/reorder",{method:"POST",headers:{"Content-Type":"application/json","X-Requested-With":"fetch"},
  body:JSON.stringify({keys:order})}).then(function(r){return r.json();}).then(function(j){
   if(j&&j.ok){location.reload();}else{alert("Не удалось сохранить порядок колонок.");}
  }).catch(function(){alert("Нет связи с сервером.");});
}
function reset(){dragKey=null;overKey=null;clearMarks();
 var a=ths();for(var i=0;i<a.length;i++)a[i].classList.remove("coldragging");}
function bind(){
 var t=document.getElementById("shthead");if(!t)return;
 t.addEventListener("dragstart",onDown);
 t.addEventListener("dragover",onOver);
 t.addEventListener("drop",onDrop);
 t.addEventListener("dragend",reset);
 var a=ths();for(var i=0;i<a.length;i++){a[i].setAttribute("draggable","true");a[i].classList.add("coldraggable");}
}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",bind);}else{bind();}
})();
