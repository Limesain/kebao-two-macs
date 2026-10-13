// 任何卡片加 ?anim=1 即入场动画，并在 dur 毫秒后把 title 置为 DONE 供录屏
(function(){const q=new URLSearchParams(location.search); if(q.get('anim')==='1'){document.body.classList.add('anim');} window.__log=window.__log||{}; setTimeout(()=>{document.title='DONE';}, +(q.get('dur')|| (q.get('anim')==='1'?7000:300)));})();
