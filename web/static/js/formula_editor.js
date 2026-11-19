
/* fe-v1: vizualnyj redaktor formul. Sobiraet tot zhe JSON {kind,op,a,b,...},
   chto chitaet service.compute_value. Ne lomayet starue markup — polya ostatayutsya,
   editor risuyetsya nad nimi i sinhroniziruet ih znacheniya. */
(function(){
"use strict";
var OP_SYM={add:"+",sub:"−",mul:"×",div:"÷"};
var OW_SYM={eq:"=",ne:"≠",contains:"содержит",gt:">",lt:"<"};
function val(n){var e=document.querySelector('[name="'+n+'"]');return e?e.value:"";}
function setv(n,v){var e=document.querySelector('[name="'+n+'"]');if(e)e.value=v;}
function fireChange(n){var e=document.querySelector('[name="'+n+'"]');if(e){e.dispatchEvent(new Event("change",{bubbles:true}));e.dispatchEvent(new Event("input",{bubbles:true}));}}
function kinds(){return [{k:"arith",t:"арифметика (+ − × ÷)"},{k:"concat",t:"склеить текст A и B"},{k:"days",t:"дни между датами"},{k:"if",t:"если … то … иначе"}];}
function buildBox(){
 var host=document.querySelector('[name="kind"]');
 if(!host)return null;
 var fs=host.closest("fieldset")||host.closest(".form-row")||host.parentNode;
 var box=document.createElement("div");box.className="fe-box";box.id="febox";
 fs.parentNode.insertBefore(box,fs.nextSibling);
 return box;
}
function render(){
 var box=document.getElementById("febox");if(!box)return;
 var ty=val("col_type");
 if(ty!=="computed"&&ty!=="ref"){box.style.display="none";return;}
 box.style.display="";
 var html='<div class="fe-head"><span class="fe-title">Выражение</span>'
  +'<button type="button" class="btn gray fe-adv">⚙ Продвинутый ввод</button></div>';
 if(ty==="ref"){
  html+='<div class="fe-ref">'
   +'Из таблицы <select class="fe-reftbl">'+refTblOpts()+'</select>, '
   +'где её <input type="text" class="fe-mrem" placeholder="ключ там" value="'+esc(val("match_remote"))+'">'
   +' равно нашей <input type="text" class="fe-mloc" placeholder="ключ здесь" value="'+esc(val("match_local"))+'">'
   +' — показать <input type="text" class="fe-show" placeholder="колонка" value="'+esc(val("show"))+'">'
   +'</div>';
 }else{
  var kd=val("kind")||"arith";
  html+='<div class="fe-kinds">';
  var ks=kinds();
  for(var i=0;i<ks.length;i++){html+='<button type="button" class="fe-kind'+(kd===ks[i].k?" on":"")+'" data-k="'+ks[i].k+'">'+ks[i].t+'</button>';}
  html+='</div><div class="fe-body" id="febody"></div>';
 }
 box.innerHTML=html;
 wireHead(box);
 if(ty!=="ref")renderBody(box,val("kind")||"arith");
 updatePreview();
}
function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;");}
function refTblOpts(){
 var sel=val("ref_table");var out='<option value="">— выбрать —</option>';
 var st=document.querySelector('[name="ref_table"]');
 if(st&&st.options){for(var i=0;i<st.options.length;i++){var o=st.options[i];out+='<option value="'+o.value+'"'+(o.value===sel?" selected":"")+'>'+esc(o.text)+'</option>';}}
 return out;
}
function wireHead(box){
 var adv=box.querySelector(".fe-adv");
 if(adv)adv.addEventListener("click",function(){var fs=document.querySelector('[name="kind"]').closest("fieldset")||document.querySelector('[name="kind"]').parentNode;fs.style.display=fs.style.display==="none"?"":"none";});
 var rt=box.querySelector(".fe-reftbl");
 if(rt)rt.addEventListener("change",function(){setv("ref_table",rt.value);fireChange("ref_table");updatePreview();});
 var mr=box.querySelector(".fe-mrem");if(mr)mr.addEventListener("input",function(){setv("match_remote",mr.value);fireChange("match_remote");updatePreview();});
 var ml=box.querySelector(".fe-mloc");if(ml)ml.addEventListener("input",function(){setv("match_local",ml.value);fireChange("match_local");updatePreview();});
 var sh=box.querySelector(".fe-show");if(sh)sh.addEventListener("input",function(){setv("show",sh.value);fireChange("show");updatePreview();});
 var kb=box.querySelectorAll(".fe-kind");
 for(var i=0;i<kb.length;i++){kb[i].addEventListener("click",function(){var k=this.getAttribute("data-k");setv("kind",k);fireChange("kind");var bs=box.querySelectorAll(".fe-kind");for(var j=0;j<bs.length;j++)bs[j].classList.toggle("on",bs[j].getAttribute("data-k")===k);renderBody(box,k);updatePreview();});}
}
function tokenPicker(cls,label,current){
 var cols=[];var opt=document.querySelector('[name="a"]');
 var dl=document.getElementById("coldl");
 if(dl){for(var i=0;i<dl.options.length;i++)cols.push({v:dl.options[i].value,t:dl.options[i].value});}
 var h='<span class="fe-tok"><span class="fe-lbl">'+esc(label)+'</span>';
 if(cols.length){
  h+='<select class="fe-'+cls+'"><option value="">— литерал —</option>';
  for(var j=0;j<cols.length;j++)h+='<option value="'+esc(cols[j].v)+'"'+(current===cols[j].v?" selected":"")+'>'+esc(cols[j].t)+'</option>';
  h+='</select><input type="text" class="fe-'+cls+'-lit" placeholder="или число/текст" value="'+(current&&cols.map(function(x){return x.v}).indexOf(current)<0?esc(current):"")+'">';
 }else{
  h+='<input type="text" class="fe-'+cls+'-lit" placeholder="'+esc(label)+'" value="'+esc(current)+'">';
 }
 h+='</span>';
 return h;
}
function renderBody(box,k){
 var body=document.getElementById("febody");if(!body)return;
 var h="";
 if(k==="arith"){
  var ops=["add","sub","mul","div"];
  h+='<div class="fe-line">'+tokenPicker("a","A",val("a"))
   +'<select class="fe-op">'+ops.map(function(o){return '<option value="'+o+'"'+(val("op")===o?" selected":"")+'>'+OP_SYM[o]+'</option>';}).join("")+'</select>'
   +tokenPicker("b","B",val("b"))+'</div>';
 }else if(k==="concat"){
  h+='<div class="fe-line">'+tokenPicker("a","A",val("a"))+'<span class="fe-plus">+</span>'+tokenPicker("b","B",val("b"))+'</div>';
 }else if(k==="days"){
  h+='<div class="fe-line">'+tokenPicker("a","от даты",val("a"))+'<span class="fe-plus">до</span>'+tokenPicker("b","до даты (пусто = сегодня)",val("b"))+'</div>';
 }else if(k==="if"){
  var ow=["eq","ne","contains","gt","lt"];
  h+='<div class="fe-line">если '+tokenPicker("if_col","колонка",val("if_col"))
   +'<select class="fe-ifop">'+ow.map(function(o){return '<option value="'+o+'"'+(val("if_op")===o?" selected":"")+'>'+OW_SYM[o]+'</option>';}).join("")+'</select>'
   +'<input type="text" class="fe-ifval" placeholder="значение" value="'+esc(val("if_val"))+'">'
   +' то <input type="text" class="fe-thenv" placeholder="ТО" value="'+esc(val("then_v"))+'">'
   +' иначе <input type="text" class="fe-elsev" placeholder="ИНАЧЕ" value="'+esc(val("else_v"))+'"></div>';
 }
 body.innerHTML=h;
 var q=function(s){return body.querySelector(s);};
 function bindAB(which){
  var lit=q(".fe-"+which+"-lit"),sel=q(".fe-"+which);
  function push(){
   var v=(sel&&sel.value)||(lit&&lit.value)||"";
   setv(which,v);fireChange(which);updatePreview();
  }
  if(lit)lit.addEventListener("input",push);
  if(sel)sel.addEventListener("change",function(){if(sel.value){if(lit)lit.value="";}push();});
 }
 bindAB("a");bindAB("b");
 var op=q(".fe-op");if(op)op.addEventListener("change",function(){setv("op",op.value);fireChange("op");updatePreview();});
 var ic=q(".fe-if_col-lit"),isc=q(".fe-if_col");
 function pushIfCol(){var v=(isc&&isc.value)||(ic&&ic.value)||"";setv("if_col",v);fireChange("if_col");updatePreview();}
 if(ic)ic.addEventListener("input",pushIfCol);
 if(isc)isc.addEventListener("change",pushIfCol);
 var io=q(".fe-ifop");if(io)io.addEventListener("change",function(){setv("if_op",io.value);fireChange("if_op");updatePreview();});
 var iv=q(".fe-ifval");if(iv)iv.addEventListener("input",function(){setv("if_val",iv.value);fireChange("if_val");updatePreview();});
 var tv=q(".fe-thenv");if(tv)tv.addEventListener("input",function(){setv("then_v",tv.value);fireChange("then_v");updatePreview();});
 var ev=q(".fe-elsev");if(ev)ev.addEventListener("input",function(){setv("else_v",ev.value);fireChange("else_v");updatePreview();});
}
function summary(){
 var ty=val("col_type");
 if(ty==="ref")return 'Из таблицы №'+(val("ref_table")||"?")+': где её «'+(val("match_remote")||"?")+'» равно нашей «'+(val("match_local")||"?")+'», показать «'+(val("show")||"?")+'»';
 var k=val("kind")||"arith";
 if(k==="arith")return '('+(val("a")||"?")+') '+ (OP_SYM[val("op")]||"?") +' ('+(val("b")||"?")+')';
 if(k==="concat")return 'склейка: '+(val("a")||"?")+' + '+(val("b")||"?");
 if(k==="days")return 'дней между '+(val("a")||"?")+' и '+(val("b")||"сегодня");
 if(k==="if")return 'если «'+(val("if_col")||"?")+'» '+(OW_SYM[val("if_op")]||"?")+' «'+(val("if_val")||"")+'» то «'+(val("then_v")||"")+'» иначе «'+(val("else_v")||"")+'»';
 return "?";
}
function updatePreview(){
 var pv=document.getElementById("feprev");
 if(!pv){pv=document.createElement("div");pv.id="feprev";pv.className="fe-prev";
  var b=document.getElementById("febox");if(b)b.appendChild(pv);}
 pv.textContent="👁 " + summary();
}
function boot(){render();}
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",boot);}else{boot();}
var ct=document.querySelector('[name="col_type"]');if(ct)ct.addEventListener("change",render);
var ki=document.querySelector('[name="kind"]');if(ki)ki.addEventListener("change",render);
})();
