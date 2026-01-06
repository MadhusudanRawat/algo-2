import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const PCRWidget = () => {
  const [pcr, setPcr] = useState(null);
  const [symbol, setSymbol] = useState('NIFTY');
  const [expiryDate, setExpiryDate] = useState('25JUL2024');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchPcr = useCallback(() => {
    setLoading(true);
    setError('');
    axios.get(`http://localhost:8000/api/pcr/${symbol}/${expiryDate}`)
      .then(response => {
        setPcr(response.data.pcr);
        setLoading(false);
      })
      .catch(error => {
        setError('Error fetching PCR data.');
        console.error('Error fetching PCR data:', error);
        setLoading(false);
      });
  }, [symbol, expiryDate]);

  useEffect(() => {
    fetchPcr();
  }, [fetchPcr]);

  return (
    <div>
      <h2>Put-Call Ratio (PCR)</h2>
      <div>
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Symbol (e.g., NIFTY)"
        />
        <input
          type="text"
          value={expiryDate}
          onChange={(e) => setExpiryDate(e.target.value)}
          placeholder="Expiry Date (e.g., 25JUL2024)"
        />
        <button onClick={fetchPcr} disabled={loading}>
          {loading ? 'Loading...' : 'Get PCR'}
        </button>
      </div>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {pcr !== null && !loading && (
        <div>
          <h3>PCR for {symbol} ({expiryDate}): {pcr.toFixed(2)}</h3>
        </div>
      )}
    </div>
  );
};

export default PCRWidget;
