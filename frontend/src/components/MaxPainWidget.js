import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const MaxPainWidget = () => {
  const [maxPain, setMaxPain] = useState(null);
  const [symbol, setSymbol] = useState('NIFTY');
  const [expiryDate, setExpiryDate] = useState('25JUL2024');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchMaxPain = useCallback(() => {
    setLoading(true);
    setError('');
    axios.get(`http://localhost:8000/api/max-pain/${symbol}/${expiryDate}`)
      .then(response => {
        setMaxPain(response.data.max_pain);
        setLoading(false);
      })
      .catch(error => {
        setError('Error fetching Max Pain data.');
        console.error('Error fetching Max Pain data:', error);
        setLoading(false);
      });
  }, [symbol, expiryDate]);

  useEffect(() => {
    fetchMaxPain();
  }, [fetchMaxPain]);

  return (
    <div>
      <h2>Max Pain</h2>
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
        <button onClick={fetchMaxPain} disabled={loading}>
          {loading ? 'Loading...' : 'Get Max Pain'}
        </button>
      </div>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {maxPain !== null && !loading && (
        <div>
          <h3>Max Pain for {symbol} ({expiryDate}): {maxPain.toFixed(2)}</h3>
        </div>
      )}
    </div>
  );
};

export default MaxPainWidget;
