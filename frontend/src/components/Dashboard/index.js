import React, { useState, useEffect } from 'react';

const Dashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/dashboard_data')
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
        setData(data);
        setLoading(false);
      })
      .catch(error => {
        setError(error.message);
        setLoading(false);
      });
  }, []);

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Live Data Analysis Dashboard</h1>

      {loading && <p>Loading...</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {data && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '20px', marginBottom: '20px' }}>
            <div style={{ border: '1px solid #ccc', padding: '10px' }}>
              <h2>Underlying Price</h2>
              <p>{data.current_price}</p>
            </div>
            <div style={{ border: '1px solid #ccc', padding: '10px' }}>
              <h2>Put-Call Ratio (PCR)</h2>
              <p>{data.pcr}</p>
            </div>
            <div style={{ border: '1px solid #ccc', padding: '10px' }}>
              <h2>Max Pain</h2>
              <p>{data.max_pain}</p>
            </div>
            <div style={{ border: '1px solid #ccc', padding: '10px' }}>
              <h2>INDIAVIX</h2>
              <p>{data.india_vix}</p>
            </div>
          </div>

          <h2>Option Chain</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div>
              <h3>Calls</h3>
              <OptionTable options={data.option_chain.calls} />
            </div>
            <div>
              <h3>Puts</h3>
              <OptionTable options={data.option_chain.puts} />
            </div>
          </div>

          <h2>Futures</h2>
          <FuturesTable futures={data.futures} />
        </div>
      )}
    </div>
  );
};

const OptionTable = ({ options }) => (
  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
    <thead>
      <tr style={{ backgroundColor: '#f2f2f2' }}>
        <th style={tableHeaderStyle}>Strike</th>
        <th style={tableHeaderStyle}>LTP</th>
        <th style={tableHeaderStyle}>IV</th>
        <th style={tableHeaderStyle}>OI</th>
        <th style={tableHeaderStyle}>OI Change</th>
        <th style={tableHeaderStyle}>Volume</th>
      </tr>
    </thead>
    <tbody>
      {options.map((option, index) => (
        <tr key={index}>
          <td style={tableCellStyle}>{option.strike_price}</td>
          <td style={tableCellStyle}>{option.ltp}</td>
          <td style={tableCellStyle}>{option.iv}</td>
          <td style={tableCellStyle}>{option.oi}</td>
          <td style={tableCellStyle}>{option.oi_change}</td>
          <td style={tableCellStyle}>{option.volume}</td>
        </tr>
      ))}
    </tbody>
  </table>
);

const FuturesTable = ({ futures }) => (
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
        <tr style={{ backgroundColor: '#f2f2f2' }}>
            <th style={tableHeaderStyle}>Expiry</th>
            <th style={tableHeaderStyle}>LTP</th>
            <th style={tableHeaderStyle}>OI</th>
            <th style={tableHeaderStyle}>OI Change</th>
            <th style={tableHeaderStyle}>Volume</th>
        </tr>
        </thead>
        <tbody>
        {futures.map((future, index) => (
            <tr key={index}>
            <td style={tableCellStyle}>{future.expiry}</td>
            <td style={tableCellStyle}>{future.ltp}</td>
            <td style={tableCellStyle}>{future.oi}</td>
            <td style={tableCellStyle}>{future.oi_change}</td>
            <td style={tableCellStyle}>{future.volume}</td>
            </tr>
        ))}
        </tbody>
    </table>
);

const tableHeaderStyle = {
  border: '1px solid #ccc',
  padding: '8px',
  textAlign: 'left',
};

const tableCellStyle = {
  border: '1px solid #ccc',
  padding: '8px',
};

export default Dashboard;
