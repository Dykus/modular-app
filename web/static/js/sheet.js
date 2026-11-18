(function(){
"use strict";
var S=window.SHEET;
var rows=S.rows.slice(), counters=S.counters, sel=[], active=null, editing=null, undoStack=[];
var filters={q:"",col:"",val:"",recent:false}, sort=null, lastTs=S.server_ts, feed=[], recent={}, dirty={};
var pending=null, dragId=null, drawerId=null, views=[];
var lastSnap=JSON.stringify(S.rows)+"|"+JSON.stringify(S.counters);
var prefs={density:"n",font:14,dark:document.body.classList.contains("dark"),zebra:true,grid:true,locks:true,recent:true,freeze:true,bands:true,pause:false};
function $(id){return document.getElementById(id);}
var root=$("shroot");
var groups=[];
S.cols.forEach(function(c){var g=c.computed?"Служебное (само)":(c.grp||"Без группы");if(groups.indexOf(g)<0)groups.push(g);});
function gi(g){var i=groups.indexOf(g);if(i<0)i=0;return i%6;}
function gcolor(g){return "var(--shg"+gi(g)+"c)";}
function gbg(g){return "var(--shg"+gi(g)+"b)";}
function grpOf(c){return c.computed?"Служебное (само)":(c.grp||"Без группы");}
function colOf(k){for(var i=0;i<S.cols.length;i++)if(S.cols[i].key===k)return S.cols[i];return null;}
function rowOf(id){for(var i=0;i<rows.length;i++)if(rows[i].id===id)return rows[i];return null;}
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(m){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m];});}
function fm(n){var v=Number(String(n).replace(/\s/g,"").replace(",","."));return isNaN(v)?esc(n):v.toLocaleString("ru-RU");}
function fd(iso){if(!iso)return"";var p=String(iso).split("-");return p.length===3?p[2]+"."+p[1]+"."+p[0]:esc(iso);}
function fw(iso){if(!iso)return"";var d=new Date(iso);return d.toLocaleDateString("ru-RU")+" "+d.toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit"});}
function toISO(v){v=String(v||"").trim();var m=v.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);if(m)return m[3]+"-"+m[2]+"-"+m[1];return /^\d{4}-\d{2}-\d{2}$/.test(v)?v:"";}
function fromISO(v){v=String(v||"").trim();var m=v.match(/^(\d{4})-(\d{2})-(\d{2})$/);if(m)return m[3]+"."+m[2]+"."+m[1];return v;}
function disp(c,v){if(c.type==="number")return fm(v);if(c.type==="date")return fd(v);return esc(v);}
function markRecent(id,key){recent[id]=recent[id]||{};recent[id][key]=Date.now();}
function isRecent(id,key){return recent[id]&&recent[id][key]&&(Date.now()-recent[id][key]<300000);}
function hasRecent(id){return recent[id]&&Object.keys(recent[id]).some(function(k){return isRecent(id,k);});}
function markDirty(id,key){dirty[id]=dirty[id]||{};dirty[id][key]=Date.now();}
function clearDirty(id,key){if(dirty[id])delete dirty[id][key];}
function isDirty(id,key){return dirty[id]&&dirty[id][key]&&(Date.now()-dirty[id][key]<20000);}
function toast(msg,kind,action){var t=document.createElement("div");t.className="t "+(kind||"");var s=document.createElement("span");s.textContent=msg;t.appendChild(s);
 if(action){var b=document.createElement("button");b.textContent=action.label;b.onclick=function(){action.fn();t.remove();};t.appendChild(b);}
 $("shtoasts").appendChild(t);setTimeout(function(){t.style.opacity="0";t.style.transition=".3s";setTimeout(function(){t.remove();},320);},action?8000:4200);}
function post(url,body){return fetch(url,{method:"POST",headers:{"Content-Type":"application/json","X-Requested-With":"fetch"},body:JSON.stringify(body||{})}).then(function(r){return r.json().then(function(j){return{status:r.status,j:j};});});}
function setPollLabel(){var el=$("shpoll");if(!el)return;
 if(editing){el.textContent="обновление отложено — идёт правка";el.style.color="#e8930c";return;}
 el.style.color="";
 if(prefs.pause){el.textContent="автообновление выключено";return;}
 el.textContent="обновлено "+new Date().toLocaleTimeString("ru-RU");}
function visible(){var out=rows.slice();var q=filters.q.trim().toLowerCase();
 if(q)out=out.filter(function(r){return S.cols.some(function(c){return String(r.cells[c.key]||"").toLowerCase().indexOf(q)>=0;});});
 if(filters.col&&filters.val!=="")out=out.filter(function(r){return String(r.cells[filters.col]||"")===filters.val;});
 if(filters.recent)out=out.filter(function(r){return hasRecent(r.id);});
 if(sort){var c=colOf(sort.key);out.sort(function(a,b){var va=a.cells[sort.key],vb=b.cells[sort.key];
  if(c&&c.type==="number"){va=Number(String(va).replace(/\s/g,"").replace(",","."))||0;vb=Number(String(vb).replace(/\s/g,"").replace(",","."))||0;}
  else if(c&&c.type==="date"){va=toISO(va)||String(va||"");vb=toISO(vb)||String(vb||"");}
  else{va=String(va||"");vb=String(vb||"");}
  return (va<vb?-1:va>vb?1:0)*sort.dir;});}
 return out;}
function applyPrefs(){root.classList.toggle("zebra",prefs.zebra);root.classList.toggle("gridlines",prefs.grid);
 root.classList.toggle("nolocks",!prefs.locks);root.classList.toggle("norecent",!prefs.recent);
 root.classList.toggle("freeze",prefs.freeze);root.classList.toggle("nobands",!prefs.bands);
 document.body.classList.toggle("dark",prefs.dark);
 var d={c:[30,7],n:[38,10],r:[48,14]}[prefs.density];
 root.style.setProperty("--shrow",d[0]+"px");root.style.setProperty("--shpad",d[1]+"px");root.style.setProperty("--shfs",prefs.font+"px");
 $("shfontv").textContent=prefs.font;}
function renderCounters(){$("shcounters").innerHTML=counters.map(function(c){return '<div class="shcard"><h4>'+esc(c.title)+'</h4><p>'+esc(c.value)+'</p></div>';}).join("");}
function render(){
 if(editing){return;}
 var box=$("shgridbox");var st=box?box.scrollTop:0,sl=box?box.scrollLeft:0;
 applyPrefs();renderCounters();
 var vr=visible(),h="";
 if(prefs.bands){h+='<tr class="shbands"><th class="shchkcol"></th><th class="shdrag"></th>';
  var i=0;while(i<S.cols.length){var g=grpOf(S.cols[i]);var n=0,j=i;
   while(j<S.cols.length&&grpOf(S.cols[j])===g){n++;j++;}
   h+='<th colspan="'+n+'" data-band="'+esc(g)+'" style="background:'+gbg(g)+';color:'+gcolor(g)+'">'+esc(g)+"</th>";i=j;}
  h+="</tr>";}
 h+='<tr class="shcols"><th class="shchkcol"><input type="checkbox" id="shchkall"></th><th class="shdrag"></th>';
 S.cols.forEach(function(c,ix){var g=grpOf(c);var sorted=sort&&sort.key===c.key;var ar=sorted?(sort.dir===1?"▲":"▼"):"↕";
  var mark=c.computed?" ⚙":(c.editable?" ✎":" 🔒");
  h+='<th class="'+(ix===0?"shfirst ":"")+(sorted?"sorted":"")+'" data-sort="'+c.key+'" style="border-top:3px solid '+gcolor(g)+'">'+esc(c.title)+mark+'<span class="ar">'+ar+"</span></th>";});
 h+="</tr>";$("shthead").innerHTML=h;
 var b="";
 vr.forEach(function(r,ri){var isSel=sel.indexOf(r.id)>=0;
  b+='<tr data-id="'+r.id+'" class="'+(isSel?"sel":"")+'" style="animation-delay:'+Math.min(ri*25,250)+'ms">';
  b+='<td class="shchkcol"><input type="checkbox" class="shrowchk" data-id="'+r.id+'" '+(isSel?"checked":"")+'></td>';
  b+='<td class="shdrag" draggable="true" data-drag="'+r.id+'">⋮⋮</td>';
  S.cols.forEach(function(c,ix){var v=r.cells[c.key];var g=grpOf(c);var cls=(ix===0?"shfirst ":"");
   if(c.type==="number")cls+="money ";if(c.type==="date")cls+="date ";
   if(c.computed)cls+="shsvc ";else if(c.editable)cls+="shown ";else cls+="shlocked ";
   if(isRecent(r.id,c.key))cls+="recent ";
   if(active&&active.id===r.id&&active.key===c.key)cls+="active ";
   var style=(!c.editable&&!c.computed)?";background:"+gbg(g):"";
   var inner=(c.type==="list"&&v)?'<span class="stb">'+esc(v)+"</span>":disp(c,v);
   var lk=(!c.editable&&!c.computed)?'<span class="lk">🔒</span>':"";
   b+='<td class="'+cls.trim()+'" data-key="'+c.key+'" data-id="'+r.id+'" style="'+style+'">'+inner+lk+"</td>";});
  b+="</tr>";});
 if(!vr.length)b='<tr><td colspan="'+(S.cols.length+2)+'"><div style="padding:30px;text-align:center;color:var(--shmut);font-style:italic">Пусто. Создай строку или сбрось фильтры.</div></td></tr>';
 $("shtbody").innerHTML=b;
 var ca=$("shchkall");if(ca)ca.checked=vr.length>0&&vr.every(function(r){return sel.indexOf(r.id)>=0;});
 $("shbulk").classList.toggle("show",sel.length>0);$("shbulkn").textContent="Выбрано: "+sel.length;
 $("shtrash").textContent=S.trash;
 if(box){box.scrollTop=st;box.scrollLeft=sl;}
 renderFeed();setPollLabel();}
function renderFeed(){if(!feed.length){$("shfeed").innerHTML='<div class="none">Изменений пока нет. Поменяй свою клетку — запись появится здесь.</div>';return;}
 $("shfeed").innerHTML=feed.slice(0,50).map(function(l){var c=colOf(l.key);var g=c?grpOf(c):"Без группы";
  return '<div class="it"><span class="who" style="background:'+gcolor(g)+'">'+esc(l.who)+'</span><span>строка №'+l.row+" · "+esc(c?c.title:l.key)+': <span class="old">'+esc(l.old||"—")+'</span> → <span class="new">'+esc(l.new||"—")+'</span></span><time>'+fw(l.ts)+"</time></div>";}).join("");}
function pushFeed(l){feed.unshift(l);if(feed.length>200)feed.pop();}
function cellTd(id,key){return $("shtbody").querySelector('td[data-id="'+id+'"][data-key="'+key+'"]');}
function applyServer(j){var map={};rows.forEach(function(r){map[r.id]=r;});
 rows=j.rows.map(function(sr){var loc=map[sr.id];
  if(loc){S.cols.forEach(function(c){if(isDirty(sr.id,c.key))sr.cells[c.key]=loc.cells[c.key];});}
  return sr;});
 counters=j.counters;S.trash=j.trash;
 lastSnap=JSON.stringify(j.rows)+"|"+JSON.stringify(j.counters);}
function afterEdit(){if(pending){var j=pending;pending=null;applyServer(j);}render();}
function openEditor(id,key,initial){var r=rowOf(id),c=colOf(key);if(!r||!c)return;
 if(c.computed){toast("Колонка «"+c.title+"» вычисляется программой.","warn");return;}
 if(!c.editable){locked(id,c);return;}
 closeEditor(true);var td=cellTd(id,key);if(!td)return;active={id:id,key:key};
 td.classList.add("editing","active");td.innerHTML="";var inp;
 if(c.type==="list"){inp=document.createElement("select");inp.innerHTML='<option value=""></option>'+c.options.map(function(o){return "<option>"+esc(o)+"</option>";}).join("");inp.value=r.cells[key]||"";}
 else{inp=document.createElement("input");inp.type=c.type==="date"?"date":"text";
  inp.value=initial!==undefined?initial:(c.type==="date"?toISO(r.cells[key]):(r.cells[key]||""));if(c.type==="number")inp.inputMode="decimal";}
 td.appendChild(inp);inp.focus();if(inp.select&&c.type!=="date")inp.select();
 editing={id:id,key:key,inp:inp,orig:r.cells[key]};
 setPollLabel();
 inp.addEventListener("keydown",function(e){e.stopPropagation();
  if(e.key==="Enter"){e.preventDefault();commit();move(0,1,true);}
  else if(e.key==="Escape"){e.preventDefault();closeEditor(true);afterEdit();}
  else if(e.key==="Tab"){e.preventDefault();commit();nextEditable(id,key,e.shiftKey?-1:1);}});
 inp.addEventListener("blur",function(){if(editing&&editing.inp===inp)commit();});}
function closeEditor(cancel){if(!editing)return;var e=editing;editing=null;
 if(cancel){var r=rowOf(e.id);if(r)r.cells[e.key]=e.orig;}
 if(e.inp.parentNode)e.inp.remove();}
function commit(){if(!editing)return;var e=editing;editing=null;
 var nv=e.inp.value;if(e.inp.parentNode)e.inp.remove();
 var r=rowOf(e.id);if(!r){afterEdit();return;}
 var c=colOf(e.key);if(c&&c.type==="date")nv=fromISO(nv);
 var old=r.cells[e.key];
 if(String(old||"")===String(nv||"")){afterEdit();return;}
 undoStack.push({id:e.id,key:e.key,old:old});if(undoStack.length>60)undoStack.shift();
 r.cells[e.key]=nv;markRecent(e.id,e.key);markDirty(e.id,e.key);afterEdit();
 post(S.urls.cell,{id:e.id,key:e.key,value:nv}).then(function(res){
  var rr=rowOf(e.id);
  if(res.status===200&&res.j.ok){if(rr)rr.cells=res.j.cells;counters=res.j.counters;lastTs=res.j.server_ts;
   clearDirty(e.id,e.key);markRecent(e.id,e.key);
   pushFeed({row:e.id,key:e.key,old:old,new:nv,who:"вы",ts:new Date().toISOString()});afterEdit();}
  else{if(rr)rr.cells[e.key]=old;clearDirty(e.id,e.key);
   toast(res.j.err==="locked"?"Колонка закрыта для вашей роли.":(res.j.err==="gone"?"Строку удалили, пока вы правили.":"Не удалось сохранить: "+(res.j.err||res.status)),"err");
   afterEdit();}});}
function locked(id,c){var td=cellTd(id,c.key);if(td){td.classList.add("shake");setTimeout(function(){td.classList.remove("shake");},350);}
 var g=grpOf(c);var band=$("shthead").querySelector('[data-band="'+g+'"]');
 if(band){band.style.filter="brightness(1.3)";setTimeout(function(){band.style.filter="";},900);}
 toast("Колонку «"+c.title+"» заполняет группа «"+g+"». Вашей роли она доступна только на чтение.","warn");}
function move(dr,dc,onlyEd){var vr=visible();if(!vr.length)return;
 var ri=active?vr.findIndex(function(x){return x.id===active.id;}):0;var ci=active?S.cols.findIndex(function(c){return c.key===active.key;}):0;
 if(ri<0)ri=0;if(ci<0)ci=0;ri=Math.max(0,Math.min(vr.length-1,ri+dr));ci=Math.max(0,Math.min(S.cols.length-1,ci+dc));
 if(onlyEd){var guard=0;while(!S.cols[ci].editable&&guard++<S.cols.length)ci=(ci+1)%S.cols.length;}
 active={id:vr[ri].id,key:S.cols[ci].key};render();var td=cellTd(active.id,active.key);if(td)td.scrollIntoView({block:"nearest",inline:"nearest"});}
function nextEditable(id,key,dir){var vr=visible();var ri=vr.findIndex(function(x){return x.id===id;});var ci=S.cols.findIndex(function(c){return c.key===key;});
 for(var s=0;s<S.cols.length*vr.length;s++){ci+=dir;var rid=id;
  if(ci>=S.cols.length){ci=0;ri++;if(ri>=vr.length)break;rid=vr[ri].id;}
  if(ci<0){ci=S.cols.length-1;ri--;if(ri<0)break;rid=vr[ri].id;}
  if(S.cols[ci].editable){openEditor(rid,S.cols[ci].key);return;}}
 render();}
function doUndo(){if(!undoStack.length){toast("Нечего отменять.","warn");return;}
 var u=undoStack.pop();var r=rowOf(u.id);if(!r)return;var cur=r.cells[u.key];
 r.cells[u.key]=u.old;markRecent(u.id,u.key);markDirty(u.id,u.key);render();
 post(S.urls.cell,{id:u.id,key:u.key,value:u.old}).then(function(res){
  if(res.j.ok){var rr=rowOf(u.id);if(rr)rr.cells=res.j.cells;counters=res.j.counters;lastTs=res.j.server_ts;
   clearDirty(u.id,u.key);pushFeed({row:u.id,key:u.key,old:cur,new:u.old,who:"вы (отмена)",ts:new Date().toISOString()});afterEdit();}
  else{clearDirty(u.id,u.key);afterEdit();}});
 toast("Отменено.","ok");}
function refresh(manual){
 if(prefs.pause&&!manual){setPollLabel();return;}
 fetch(S.urls.data+"?since="+encodeURIComponent(lastTs)).then(function(r){return r.json();}).then(function(j){
  lastTs=j.server_ts;
  if(j.changes&&j.changes.length){j.changes.forEach(function(ch){markRecent(ch.row,ch.key);pushFeed(ch);});
   toast("Чужие правки: "+j.changes.length+". Клетки подсвечены зелёным.","ok");}
  var snap=JSON.stringify(j.rows)+"|"+JSON.stringify(j.counters);
  var same=(snap===lastSnap);
  if(editing){pending=j;setPollLabel();renderFeed();return;}
  if(!same||manual){applyServer(j);render();}
  else{renderFeed();setPollLabel();}
 }).catch(function(){var el=$("shpoll");if(el)el.textContent="связь потеряна — повтор через 10 с";});}
setInterval(function(){refresh(false);},10000);
window.addEventListener("focus",function(){refresh(false);});
$("shtbody").addEventListener("click",function(e){
 var chk=e.target.closest(".shrowchk");if(chk){var id=Number(chk.dataset.id);sel=chk.checked?sel.concat([id]):sel.filter(function(x){return x!==id;});render();return;}
 if(e.target.closest("td.editing"))return; /* edit-click-guard */
 var td=e.target.closest("td[data-key]");if(!td)return;var id=Number(td.dataset.id),key=td.dataset.key;active={id:id,key:key};
 openEditor(id,key);});
$("shthead").addEventListener("click",function(e){
 if(e.target.id==="shchkall"){var vr=visible();sel=e.target.checked?vr.map(function(r){return r.id;}):[];render();return;}
 var th=e.target.closest("th[data-sort]");if(!th)return;var k=th.dataset.sort;
 if(!sort||sort.key!==k)sort={key:k,dir:1};else if(sort.dir===1)sort={key:k,dir:-1};else sort=null;render();});
document.addEventListener("keydown",function(e){
 if(editing)return;var tag=(e.target.tagName||"").toLowerCase();if(tag==="input"||tag==="select"||tag==="textarea")return;
 if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="z"){e.preventDefault();doUndo();return;}
 if(e.key==="Escape"){closeDrawer();active=null;render();return;}
 if(!active)return;
 if(e.key==="ArrowDown"){e.preventDefault();move(1,0);}else if(e.key==="ArrowUp"){e.preventDefault();move(-1,0);}
 else if(e.key==="ArrowRight"){e.preventDefault();move(0,1);}else if(e.key==="ArrowLeft"){e.preventDefault();move(0,-1);}
 else if(e.key==="Enter"||e.key==="F2"){e.preventDefault();openEditor(active.id,active.key);}
 else if(e.key==="Tab"){e.preventDefault();nextEditable(active.id,active.key,e.shiftKey?-1:1);}
 else if(e.key.length===1&&!e.ctrlKey&&!e.metaKey&&!e.altKey){var c=colOf(active.key);
  if(c&&c.editable&&c.type!=="list"&&c.type!=="date"){e.preventDefault();openEditor(active.id,active.key,e.key);}}});
$("shq").addEventListener("input",function(e){filters.q=e.target.value;render();});
$("shfcol").addEventListener("change",function(e){filters.col=e.target.value;filters.val="";fillVals();render();});
$("shfval").addEventListener("change",function(e){filters.val=e.target.value;render();});
$("shover").addEventListener("change",function(e){filters.recent=e.target.checked;render();});
function fillCols(){$("shfcol").innerHTML='<option value="">Фильтр: колонка…</option>'+S.cols.map(function(c){return '<option value="'+c.key+'">'+esc(c.title)+"</option>";}).join("");
 $("shbulkcol").innerHTML=S.cols.filter(function(c){return c.editable;}).map(function(c){return '<option value="'+c.key+'">'+esc(c.title)+"</option>";}).join("");}
function fillVals(){var c=colOf(filters.col);var opts=c?c.options:[];var seen={};rows.forEach(function(r){var v=r.cells[filters.col];if(v)seen[v]=1;});
 var list=opts.length?opts:Object.keys(seen);
 $("shfval").innerHTML='<option value="">значение…</option>'+list.map(function(o){return "<option>"+esc(o)+"</option>";}).join("");}
$("shnew").addEventListener("click",function(){post(S.urls.row,{}).then(function(res){
 if(!res.j.ok){toast("Нет права создавать строки.","err");return;}
 rows.push(res.j.row);lastTs=res.j.server_ts;render();
 var firstEd=S.cols.filter(function(c){return c.editable;})[0];
 if(firstEd){active={id:res.j.row.id,key:firstEd.key};openEditor(res.j.row.id,firstEd.key);}
 $("shgridbox").scrollTop=$("shgridbox").scrollHeight;});});
$("shbulkclear").addEventListener("click",function(){sel=[];render();});
$("shbulkapply").addEventListener("click",function(){var key=$("shbulkcol").value,val=$("shbulkval").value;var ids=sel.slice();
 post(S.urls.bulk,{ids:ids,key:key,value:val}).then(function(res){if(!res.j.ok){toast("Колонка закрыта для вашей роли.","err");return;}
  toast("Применено к "+res.j.n+" строкам.","ok");sel=[];refresh(true);});});
$("shbulkdel").addEventListener("click",function(){var ids=sel.slice();var n=ids.length;
 post(S.urls.bulk,{ids:ids,action:"delete"}).then(function(res){if(!res.j.ok){toast("Нет права удалять.","err");return;}
  sel=[];refresh(true);
  toast("В корзину: "+n+" строк.","err",{label:"Отменить",fn:function(){
   Promise.all(ids.map(function(id){return post(S.urls.row+"/"+id+"/restore",{});})).then(function(){refresh(true);toast("Строки возвращены из корзины.","ok");});}});});});
$("shcsv").addEventListener("click",function(){var head=S.cols.map(function(c){return c.title;}).join(";");
 var lines=visible().map(function(r){return S.cols.map(function(c){return '"'+String(r.cells[c.key]==null?"":r.cells[c.key]).replace(/"/g,'""')+'"';}).join(";");});
 var blob=new Blob(["\uFEFF"+head+"\n"+lines.join("\n")],{type:"text/csv;charset=utf-8"});
 var a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="sheet_"+S.tid+".csv";a.click();setTimeout(function(){URL.revokeObjectURL(a.href);},2000);
 toast("CSV выгружен.","ok");});
$("shprint").addEventListener("click",function(){window.print();});
function bind(id,key,cast){var el=$(id);if(!el)return;el.addEventListener("change",function(e){prefs[key]=cast?cast(e.target):e.target.checked;applyPrefs();render();setPollLabel();});}
bind("shdensity","density",function(t){return t.value;});bind("shfont","font",function(t){return Number(t.value);});
bind("shdark","dark");bind("shzebra","zebra");bind("shgrid","grid");bind("shlocks","locks");bind("shrecent","recent");bind("shfreeze","freeze");bind("shbands","bands");bind("shpause","pause");
$("shfont").addEventListener("input",function(e){prefs.font=Number(e.target.value);root.style.setProperty("--shfs",prefs.font+"px");$("shfontv").textContent=prefs.font;});
if($("shrefresh"))$("shrefresh").addEventListener("click",function(){refresh(true);toast("Обновлено вручную.","ok");});
function loadViews(){fetch(S.urls.views).then(function(r){return r.json();}).then(function(j){views=j.views;
 $("shviews").innerHTML='<option value="">Виды…</option>'+views.map(function(v){return '<option value="'+v.id+'">'+esc(v.name)+"</option>";}).join("");});}
$("shsaveview").addEventListener("click",function(){var name=prompt("Название вида:","Мой вид");if(!name)return;
 post(S.urls.views,{name:name,payload:{filters:filters,sort:sort,prefs:prefs}}).then(function(){loadViews();toast("Вид сохранён.","ok");});});
$("shdelview").addEventListener("click",function(){var id=Number($("shviews").value);if(!id)return;
 fetch(S.urls.views+"?id="+id,{method:"DELETE"}).then(function(){loadViews();toast("Вид удалён.","ok");});});
$("shviews").addEventListener("change",function(e){var id=Number(e.target.value);var v=null;views.forEach(function(x){if(x.id===id)v=x;});if(!v)return;
 filters=Object.assign({q:"",col:"",val:"",recent:false},v.payload.filters);sort=v.payload.sort||null;prefs=Object.assign(prefs,v.payload.prefs||{});
 $("shq").value=filters.q;$("shfcol").value=filters.col;fillVals();$("shfval").value=filters.val;$("shover").checked=filters.recent;
 $("shdensity").value=prefs.density;$("shfont").value=prefs.font;$("shdark").checked=prefs.dark;$("shzebra").checked=prefs.zebra;
 $("shgrid").checked=prefs.grid;$("shlocks").checked=prefs.locks;$("shrecent").checked=prefs.recent;$("shfreeze").checked=prefs.freeze;$("shbands").checked=prefs.bands;
 if($("shpause"))$("shpause").checked=prefs.pause;
 render();toast("Вид «"+v.name+"» применён.","ok");});
$("shtbody").addEventListener("dragstart",function(e){var h=e.target.closest("[data-drag]");if(!h)return;dragId=Number(h.dataset.drag);h.closest("tr").classList.add("dragging");});
$("shtbody").addEventListener("dragover",function(e){if(!dragId)return;e.preventDefault();var tr=e.target.closest("tr[data-id]");if(!tr||Number(tr.dataset.id)===dragId)return;
 var rc=tr.getBoundingClientRect();var before=e.clientY<rc.top+rc.height/2;
 $("shtbody").querySelectorAll("tr").forEach(function(x){x.classList.remove("dropbefore","dropafter");});
 tr.classList.add(before?"dropbefore":"dropafter");});
$("shtbody").addEventListener("drop",function(e){if(!dragId)return;e.preventDefault();var tr=e.target.closest("tr[data-id]");if(!tr)return;
 var rc=tr.getBoundingClientRect();var before=e.clientY<rc.top+rc.height/2;
 var from=rows.findIndex(function(x){return x.id===dragId;});var moved=rows.splice(from,1)[0];
 var to=rows.findIndex(function(x){return x.id===Number(tr.dataset.id);});if(!before)to++;
 rows.splice(to,0,moved);dragId=null;render();
 post(S.urls.reorder,{ids:rows.map(function(r){return r.id;})}).then(function(){toast("Порядок сохранён.","ok");});});
$("shtbody").addEventListener("dragend",function(){dragId=null;$("shtbody").querySelectorAll("tr").forEach(function(x){x.classList.remove("dragging","dropbefore","dropafter");});});
function openDrawer(id){drawerId=id;var r=rowOf(id);if(!r)return;
 $("shdtitle").textContent="Строка №"+id;
 var html=S.cols.map(function(c){return '<div class="df"><span class="k">'+esc(c.title)+'</span><span class="v">'+disp(c,r.cells[c.key])+"</span></div>";}).join("");
 html+='<h3 style="margin:12px 0 6px;font-size:12px;text-transform:uppercase;color:#68788f">История строки</h3><div id="shdhist">…</div>';
 $("shdbody").innerHTML=html;$("shdrawer").classList.add("open");$("shscrim").classList.add("show");
 fetch(S.urls.history+"?rid="+id).then(function(x){return x.json();}).then(function(j){
  $("shdhist").innerHTML=j.logs.length?j.logs.map(function(l){var c=colOf(l.key);
   return '<div class="df"><span class="k">'+fw(l.ts)+'</span><span class="v">'+esc(l.who)+": "+esc(l.old||"—")+" → "+esc(l.new||"—")+
    (c&&c.editable?'<button class="rv" data-log="'+l.id+'">вернуть старое</button>':"")+"</span></div>";}).join(""):'<div style="color:#68788f;font-style:italic">Пока нет.</div>';});}
function closeDrawer(){drawerId=null;$("shdrawer").classList.remove("open");$("shscrim").classList.remove("show");}
$("shdclose").addEventListener("click",closeDrawer);$("shscrim").addEventListener("click",closeDrawer);
$("shtbody").addEventListener("contextmenu",function(e){var tr=e.target.closest("tr[data-id]");if(tr){e.preventDefault();openDrawer(Number(tr.dataset.id));}});
$("shdbody").addEventListener("click",function(e){var b=e.target.closest(".rv");if(!b)return;
 post(S.urls.revert,{log_id:Number(b.dataset.log)}).then(function(res){if(res.j.ok){toast("Старое значение возвращено.","ok");refresh(true);openDrawer(drawerId);}else toast("Колонка закрыта для вашей роли.","err");});});
function moveRow(dir){if(!drawerId)return;var i=rows.findIndex(function(x){return x.id===drawerId;});var j=i+dir;if(j<0||j>=rows.length)return;
 var m=rows.splice(i,1)[0];rows.splice(j,0,m);render();post(S.urls.reorder,{ids:rows.map(function(r){return r.id;})});openDrawer(drawerId);}
$("shdup").addEventListener("click",function(){moveRow(-1);});$("shddown").addEventListener("click",function(){moveRow(1);});
$("shddel").addEventListener("click",function(){if(!drawerId)return;var id=drawerId;
 post(S.urls.row+"/"+id+"/delete",{}).then(function(res){if(!res.j.ok){toast("Нет права удалять.","err");return;}
  closeDrawer();refresh(true);toast("Строка в корзине.","err",{label:"Отменить",fn:function(){post(S.urls.row+"/"+id+"/restore",{}).then(function(){refresh(true);});}});});});
fillCols();fillVals();loadViews();render();setPollLabel();
toast("Правка защищена: автообновление подождёт, пока вы редактируете клетку.","ok");
})();
