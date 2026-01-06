import React, {useState, useEffect, useCallback} from 'react';
import axios from 'axios';
import StraddleCard from './StraddleCard';

const StraddleDashboard = () => {
  const [symbol, setSymbol] = useState('NIFTY');
  const [expiry, setExpiry] = useState('');
  const [interval, setInterval] = useState('15minute');
  const [topN, setTopN] = useState(10);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchAll = useCallback(async () => {
    setLoading(true); setError('');
    try {
      // Try consolidated metrics endpoint first
      const metricsPromise = axios.get(`http://localhost:8000/api/metrics/${symbol}/${expiry}`)
        .catch(() => null);

      // Option historical + greeks
      const histPromise = axios.get(`http://localhost:8000/api/historical/options/${symbol}/${expiry}?interval=${interval}`)
        .catch(() => null);

      // PCR fallback
      const pcrPromise = axios.get(`http://localhost:8000/api/pcr/${symbol}/${expiry}`).catch(()=>null);

      const [metricsRes, histRes, pcrRes] = await Promise.all([metricsPromise, histPromise, pcrPromise]);

      const metrics = metricsRes?.data || {};
      const hist = histRes?.data || {};
      const pcr = pcrRes?.data?.pcr ?? metrics.pcr ?? null;

      // Build per-strike entries from historical + metrics
      let strikes = [];
      if (hist && Object.keys(hist).length>0) {
        // hist expected shape: { expiry: { calls: {strike: entry}, puts: {...} }, ... }
        const expData = hist[expiry] || hist;
        const calls = expData?.calls || {};
        const puts = expData?.puts || {};
        const strikeSet = new Set([...Object.keys(calls||{}).map(Number), ...Object.keys(puts||{}).map(Number)]);
        strikes = Array.from(strikeSet).sort((a,b)=>a-b).slice(0, topN);
        const entries = strikes.map(s => {
          const c = calls[s] || {};
          const p = puts[s] || {};
          return {
            strike: s,
            call: c,
            put: p,
            oi_call: c?.oi ?? null,
            oi_put: p?.oi ?? null,
            oi_change_call: c?.oi_change ?? null,
            oi_change_put: p?.oi_change ?? null,
            iv_call: c?.greeks?.impliedVolatility ?? c?.iv ?? null,
            iv_put: p?.greeks?.impliedVolatility ?? p?.iv ?? null,
            volume_call: c?.volume ?? null,
            volume_put: p?.volume ?? null,
          };
        });
        setData({metrics, pcr, entries});
      } else if (metrics && metrics.oi_summary) {
        // metrics endpoint may provide oi_summary map
        const oiMap = metrics.oi_summary || {};
        const strikesArr = Object.keys(oiMap).map(Number).sort((a,b)=>a-b).slice(0, topN);
        const entries = strikesArr.map(s => ({
          strike: s,
          oi_call: oiMap[s]?.call_oi ?? null,
          oi_put: oiMap[s]?.put_oi ?? null,
          iv_call: oiMap[s]?.call_iv ?? null,
          iv_put: oiMap[s]?.put_iv ?? null,
        }));
        setData({metrics, pcr, entries});
      } else {
        setData({metrics: metrics||{}, pcr, entries: []});
      }

    } catch (e) {
      console.error(e);
      setError('Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  }, [symbol, expiry, interval, topN]);

  useEffect(()=>{ fetchAll(); }, [fetchAll]);

  return (
    <div style={{padding:16}}>
      <h2>Straddle / Strangle Dashboard</h2>
      <div style={{display:'flex', gap:8, marginBottom:12}}>
        <input value={symbol} onChange={e=>setSymbol(e.target.value)} placeholder="Symbol" />
        <input value={expiry} onChange={e=>setExpiry(e.target.value)} placeholder="Expiry (e.g., 25DEC2025)" />
        <select value={interval} onChange={e=>setInterval(e.target.value)}>
          <option value="1minute">1m</option>
          <option value="5minute">5m</option>
          <option value="15minute">15m</option>
          <option value="day">Day</option>
        </select>
        <input type="number" value={topN} onChange={e=>setTopN(Number(e.target.value))} style={{width:80}} />
        <button onClick={fetchAll} disabled={loading}>{loading? 'Refreshing...':'Refresh'}</button>
      </div>

      {error && <div style={{color:'red'}}>{error}</div>}

      <div style={{display:'flex', gap:12, marginBottom:12}}>
        <div style={{flex:1, padding:12, border:'1px solid #ddd', borderRadius:6}}>
          <div style={{fontSize:12, color:'#666'}}>PCR</div>
          <div style={{fontSize:20, fontWeight:700}}>{data?.pcr ?? '-'}</div>
        </div>
        <div style={{flex:1, padding:12, border:'1px solid #ddd', borderRadius:6}}>
          <div style={{fontSize:12, color:'#666'}}>Max Pain</div>
          <div style={{fontSize:20, fontWeight:700}}>{data?.metrics?.max_pain?.max_pain ?? '-'}</div>
        </div>
        <div style={{flex:1, padding:12, border:'1px solid #ddd', borderRadius:6}}>
          <div style={{fontSize:12, color:'#666'}}>INDIAVIX</div>
          <div style={{fontSize:20, fontWeight:700}}>{data?.metrics?.indiavix ?? data?.metrics?.vix ?? '-'}</div>
        </div>
      </div>

      <div>
        {data?.entries?.length > 0 ? (
          data.entries.map(e => <StraddleCard key={e.strike} entry={e} />)
        ) : (
          <div style={{color:'#666'}}>No strike entries available for the selected symbol/expiry.</div>
        )}
      </div>
    </div>
  );
};

export default StraddleDashboard;
