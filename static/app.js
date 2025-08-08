let chart, candleSeries, ema9Series, ema21Series;
const chartDiv = document.getElementById('chart');

function initChart(){
  if(chart) return;
  chart = LightweightCharts.createChart(chartDiv, { width: chartDiv.clientWidth, height: 360, layout:{background:{type:'solid', color:'#151823'}, textColor:'#e6e6e6'}, grid:{vertLines:{color:'#1f2332'}, horzLines:{color:'#1f2332'}}, timeScale:{timeVisible:true, secondsVisible:false} });
  candleSeries = chart.addCandlestickSeries();
  ema9Series = chart.addLineSeries({ lineWidth: 1 });
  ema21Series = chart.addLineSeries({ lineWidth: 1 });
  window.addEventListener('resize', ()=>{ chart.applyOptions({ width: chartDiv.clientWidth }); });
}

async function fetchSnapshot(){
  const r = await fetch('/api/snapshot');
  return r.json();
}

async function refresh(){
  const s = await fetchSnapshot();
  document.getElementById('mode').innerText = 'Modalità: ' + s.mode;
  document.getElementById('free_usdt').innerText = (s.free_usdt||0).toFixed(2);
  document.getElementById('pnl_today').innerText = (s.today_pnl>=0?'+':'') + (s.today_pnl||0).toFixed(2) + ' USDT';
  document.getElementById('symbol').innerText = s.active_symbol;
  document.getElementById('price').innerText = s.price ? s.price.toFixed(4) : '...';
  document.getElementById('avoided').innerText = s.today_avoided||0;
  document.getElementById('stake').value = s.stake_usdt;
  document.getElementById('tp').value = s.tp;
  document.getElementById('sl').value = s.sl;

  // trades
  const tb = document.querySelector('#trades tbody');
  tb.innerHTML='';
  (s.trades||[]).slice().reverse().forEach(t=>{
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${(t.time||'').slice(11,19)}</td><td>${t.symbol||''}</td><td>${t.side||''}</td><td>${(t.price||0).toFixed? t.price.toFixed(4): t.price}</td><td>${t.qty||''}</td><td>${t.pnl!==undefined? (t.pnl>=0?'+':'')+t.pnl : ''}</td>`;
    tb.appendChild(tr);
  });

  // pnl by symbol
  const tb2 = document.querySelector('#pnlBySymbol tbody');
  tb2.innerHTML='';
  for(const k in (s.pnl_by_symbol||{})){
    const v = s.pnl_by_symbol[k];
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${k}</td><td>${(v>=0?'+':'') + v.toFixed(4)}</td>`;
    tb2.appendChild(tr);
  }

  // load chart data (public klines for speed)
  await loadChart(s.active_symbol);
}

async function loadChart(symbol){
  initChart();
  const url = `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=1m&limit=100`;
  const r = await fetch(url);
  const kl = await r.json();
  const candles = kl.map(k=>({ time: Math.floor(k[0]/1000), open: parseFloat(k[1]), high: parseFloat(k[2]), low: parseFloat(k[3]), close: parseFloat(k[4]) }));
  candleSeries.setData(candles);
  // ema calc on close
  const closes = candles.map(c=>c.close);
  const ema9 = computeEMA(closes, 9);
  const ema21 = computeEMA(closes, 21);
  ema9Series.setData(candles.map((c,i)=>({ time:c.time, value: ema9[i] })));
  ema21Series.setData(candles.map((c,i)=>({ time:c.time, value: ema21[i] })));
}

function computeEMA(vals, period){
  if (vals.length===0) return [];
  const k = 2/(period+1);
  let out = [];
  let prev = vals[0];
  out.push(prev);
  for (let i=1;i<vals.length;i++){
    prev = vals[i]*k + prev*(1-k);
    out.push(prev);
  }
  return out;
}

// buttons
async function post(url, data){ 
  const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data||{})});
  return r.json();
}
document.getElementById('btnStart').onclick = ()=> post('/api/start',{}).then(refresh);
document.getElementById('btnStop').onclick = ()=> post('/api/stop',{}).then(refresh);
document.getElementById('btnPair').onclick = ()=> post('/api/set_symbol', {symbol: document.getElementById('pair').value}).then(refresh);
document.getElementById('btnStake').onclick = ()=> post('/api/set_stake', {stake: parseFloat(document.getElementById('stake').value)}).then(refresh);
document.getElementById('btnTPSL').onclick = ()=> post('/api/set_tp_sl', {tp: parseFloat(document.getElementById('tp').value), sl: parseFloat(document.getElementById('sl').value)}).then(refresh);
document.getElementById('btnDemo').onclick = ()=> post('/api/mode', {mode:'DEMO'}).then(refresh);
document.getElementById('btnReal').onclick = ()=> {
  const api_key = prompt('Inserisci API Key REALE (spot only, NO withdraw):');
  const api_secret = prompt('Inserisci Secret Key REALE:');
  if(api_key && api_secret){
    return post('/api/mode', {mode:'REALE', api_key, api_secret}).then(refresh);
  }
};

refresh();
setInterval(refresh, 5000);
