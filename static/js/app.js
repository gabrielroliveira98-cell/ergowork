'use strict';
var _toastT;
function showToast(msg, ms) {
  ms = ms||2800;
  var t = document.getElementById('toast');
  if(!t) return;
  t.textContent = msg;
  t.classList.remove('hidden','fade');
  clearTimeout(_toastT);
  _toastT = setTimeout(function(){
    t.classList.add('fade');
    setTimeout(function(){t.classList.add('hidden')},350);
  }, ms);
}
document.addEventListener('touchstart',function(){},{passive:true});
