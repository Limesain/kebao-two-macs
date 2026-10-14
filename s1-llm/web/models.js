// 六位选手的统一标识（画廊 / 对比 / 动图 / 卡片共用）
window.MODELS = {
  zimage:   {name:'Z-Image Turbo',        vendor:'Tongyi-MAI',   where:'local', params:'6B',  weight:'bf16 · 12.3 GB', encoder:'Qwen3-4B 8.0 GB',       steps:'9 步 · cfg 1'},
  qwen:     {name:'Qwen-Image 2.1',       vendor:'阿里 Qwen',    where:'local', params:'≈7B', weight:'bf16 · 14.2 GB', encoder:'Qwen3-VL-8B int8 9.4 GB', steps:'25 步 · cfg 1'},
  krea2:    {name:'Krea 2 Turbo',         vendor:'Krea',         where:'local', params:'≈13B',weight:'bf16 · 26.3 GB', encoder:'Qwen3-VL-4B int8 5.2 GB', steps:'8 步 · cfg 1'},
  seedream: {name:'Seedream 5.0 Pro',     vendor:'字节跳动 Seed', where:'cloud', params:'未公开', weight:'API · 2K', encoder:'', steps:''},
  grok:     {name:'Grok Imagine Image 2.0', vendor:'xAI',        where:'cloud', params:'未公开', weight:'API · 2K', encoder:'', steps:''},
  gptimage: {name:'GPT-Image 2.5 Flare',  vendor:'OpenAI',       where:'cloud', params:'未公开', weight:'API · high', encoder:'', steps:''}
};
// 画廊/对比用的两行标识：第一行 大字模型名 + 徽章，第二行 参数
window.modelLabel = function(it){
  const m = window.MODELS[it.engine] || {name: it.model || it.engine || '', where: it.where || 'local', params:'', weight:''};
  const local = m.where === 'local';
  const badge = local ? '<i class="bd l">本地 · MAC STUDIO</i>' : '<i class="bd c">云端 · API</i>';
  const x = [];
  if (local) { if (m.params) x.push(m.params + ' 参数'); if (m.weight) x.push(m.weight); if (it.steps) x.push(it.steps + ' 步'); if (it.wall_s != null) x.push(it.wall_s + ' s'); }
  else { if (m.vendor) x.push(m.vendor); if (it.cost_usd != null) x.push('$' + (+it.cost_usd).toFixed(3) + ' / 张'); if (it.wall_s != null) x.push('往返 ' + it.wall_s + ' s'); }
  if (it.width) x.push(it.width + '×' + it.height);
  return `<div class="ml"><b>${m.name}</b>${badge}</div><div class="mp">${x.join(' · ')}</div>`;
};
