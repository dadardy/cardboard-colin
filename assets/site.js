(() => {
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;!?¡¿'\"‘’“”‚„«»-–—_()[]{}/\\|&@#$%*+−=×<>^~`•·…©§°¢£€¥ÀÁÂÃÄÅÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝàáâãäåèéêëìíîïñòóôõöùúûüý";
  const grid = $('#grid'), big = $('#glyphbig');
  for (const c of chars) {
    const b = document.createElement('button'); b.textContent = c; b.title = 'U+' + c.codePointAt(0).toString(16).toUpperCase().padStart(4, '0');
    const show = () => { big.textContent = c; $$('.grid button.on').forEach(x => x.classList.remove('on')); b.classList.add('on'); };
    b.addEventListener('mouseenter', show); b.addEventListener('click', show); b.addEventListener('focus', show);
    grid.appendChild(b);
  }

  const toast = $('#toast'); let t;
  const say = (msg) => { toast.textContent = msg; toast.classList.add('show'); clearTimeout(t); t = setTimeout(() => toast.classList.remove('show'), 1600); };
  $$('.copy').forEach(b => b.addEventListener('click', async () => {
    const text = $('#' + b.dataset.target).textContent;
    try { await navigator.clipboard.writeText(text); }
    catch { const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
    b.textContent = 'Copied!'; setTimeout(() => (b.textContent = 'Copy'), 1500); say('Copied to clipboard');
  }));
})();
