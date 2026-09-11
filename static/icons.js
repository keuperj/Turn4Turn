const paths={
  face:'M12 3l8 17-8-5-8 5z',peek:'M3 3v18h6M10 9s3-4 6-4 6 4 6 4-3 4-6 4-6-4-6-4M17 9h.01M11 18h10M18 15l3 3-3 3',
  move:'M12 3v18M3 12h18M8 7l4-4 4 4M8 17l4 4 4-4M7 8l-4 4 4 4M17 8l4 4-4 4',
  attack:'M12 2v4M12 18v4M2 12h4M18 12h4M19 12a7 7 0 1 1-14 0 7 7 0 0 1 14 0M12 10v4M10 12h4',
  confirm:'M4 12l5 5L20 6',cancel:'M5 5l14 14M19 5L5 19',
  reload:'M20 7v5h-5M4 17v-5h5M5 8a8 8 0 0 1 13-3l2 3M4 16l2 3a8 8 0 0 0 13-3',
  watch:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  standing:'M13.5 4a2 2 0 1 1-4 0 2 2 0 0 1 4 0M11.5 6.5v7M8 9l3.5-1.5 4 2.5M11.5 13.5l-3 7.5M11.5 13.5l4 7.5M14 10l7-2M18 8.7l1 3.3',
  kneeling:'M12.5 4a2 2 0 1 1-4 0 2 2 0 0 1 4 0M10.5 6.5l1 6.5M8 9l3-1.5 4 2.5M11.5 13l-5 3v5M11.5 13l5 4h5M14 10l7-2M18 8.7l1 3.3',
  prone:'M5 12.5a2 2 0 1 1-4 0 2 2 0 0 1 4 0M5.5 13.5l7.5 1 4 3M7 14l2.5 5H15M13 14.5l8-2.5M17.5 13l1 3',
  single:'M8 4h8l-1 9-3 2-3-2zM10 17h4v4h-4M11 7h2',auto:'M3 5h5l-.7 6-1.8 1.5L3.7 11zM9.5 5h5l-.7 6-1.8 1.5-1.8-1.5zM16 5h5l-.7 6-1.8 1.5-1.8-1.5zM4.5 15v4M12 15v4M19.5 15v4',
  door:'M4 21V3h14v18M8 21V5l10-2M8 21l10-3M13 12h1M2 21h20',
  window:'M3 3h18v18H3zM3 12h18M12 3v18',
  up:'M5 15l7-7 7 7M12 8v13',down:'M5 9l7 7 7-7M12 3v13',
  end:'M4 4v16l12-8zM20 4v16',new:'M12 4v16M4 12h16',
  help:'M9 8a3 3 0 1 1 5 2c-2 1-2 2-2 3M12 17h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
  armory:'M3 7h18v14H3zM8 7V3h8v4M3 12h18M10 10h4v4h-4z',
  focus:'M3 8V3h5M16 3h5v5M21 16v5h-5M8 21H3v-5M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  home:'M3 11l9-8 9 8M5 10v11h14V10M10 21v-7h4v7',
  deploy:'M12 2l8 4v6c0 5-8 10-8 10S4 17 4 12V6zM8 11l3 3 5-6',
  map:'M2 5l7-3 6 3 7-3v17l-7 3-6-3-7 3zM9 2v17M15 5v17',
  sound:'M3 9h4l5-5v16l-5-5H3zM16 8a6 6 0 0 1 0 8M19 5a10 10 0 0 1 0 14'
};
export function icon(name){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name]||paths.attack}"/></svg>`;}
export function button(id,name,hint,disabled=false,active=false){return `<button ${id?`id="${id}"`:''} class="icon-button ${active?'active':''}" title="${hint}" aria-label="${hint}" ${disabled?'disabled':''}>${icon(name)}</button>`;}
export function hydrate(){document.querySelectorAll('[data-icon]').forEach(b=>{b.innerHTML=icon(b.dataset.icon);b.classList.add('icon-button');b.setAttribute('aria-label',b.title);});}
