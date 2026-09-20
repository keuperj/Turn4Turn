/** Present server-owned lessons alongside the normal game controls. */
const $=id=>document.getElementById(id);

/** Render the current instruction and constrain controls to its real gameplay task. */
export function renderTutorial(state,busy,{restart,exit,focus}){
 for(const el of document.querySelectorAll('.tutorial-highlight'))el.classList.remove('tutorial-highlight');
 const training=state.tutorial,panel=$('tutorial-guide');panel.hidden=!training||training.complete;
 if(panel.hidden)return;
 const lesson=training.lesson;
 if(panel.dataset.step!==String(training.step)){
  panel.dataset.step=String(training.step);
  $('tutorial-progress').textContent=`TRAINING · STEP ${training.step+1} OF ${training.total}`;
  $('tutorial-title').textContent=lesson.title;$('tutorial-instruction').textContent=lesson.text;
 }
 $('tutorial-meter').max=training.total;$('tutorial-meter').value=training.step;
 $('tutorial-restart').onclick=restart;$('tutorial-exit').onclick=exit;
 $('tutorial-restart').disabled=busy;$('tutorial-exit').disabled=busy;
 $('tutorial-focus').hidden=lesson.x===undefined;
 $('tutorial-focus').disabled=busy;$('tutorial-focus').onclick=()=>focus(lesson);
 for(const control of document.querySelectorAll('#details button,#end')){
   const allowed=lesson.controls.some(selector=>control.matches(selector));
   control.disabled=busy||!allowed||control.disabled;
   if(allowed)control.classList.add('tutorial-highlight');
 }
}
