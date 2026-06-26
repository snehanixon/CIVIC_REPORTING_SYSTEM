// Smooth reveals and counters for the colourful dark theme
document.addEventListener('DOMContentLoaded', function(){
  // reveal elements
  const reveals = document.querySelectorAll('.reveal');
  function revealLoop(){
    for(const el of reveals){
      const r = el.getBoundingClientRect();
      if(r.top < window.innerHeight - 80) el.classList.add('visible');
    }
  }
  window.addEventListener('scroll', revealLoop);
  revealLoop();

  // animate counters when in view
  const counters = document.querySelectorAll('.stat-num');
  function animateCounter(el,target){
    let start = 0;
    const duration = 1200;
    const startTime = performance.now();
    function step(now){
      const prog = Math.min(1,(now-startTime)/duration);
      el.textContent = Math.floor(prog*target);
      if(prog<1) requestAnimationFrame(step); else el.textContent = target;
    }
    requestAnimationFrame(step);
  }
  function checkCounters(){
    for(const c of counters){
      if(c.dataset.animated) continue;
      const r = c.getBoundingClientRect();
      if(r.top < window.innerHeight - 40){ c.dataset.animated = '1'; animateCounter(c, Number(c.dataset.target)||0); }
    }
  }
  window.addEventListener('scroll', checkCounters);
  checkCounters();
});
