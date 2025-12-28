import React, { useState, useEffect } from 'react';
import './Dashboard.css';

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
    <div className="dashboard-container">
      <h1>Live Data Analysis Dashboard</h1>

      {loading && <p>Loading...</p>}
      {error && <p className="error-message">Error: {error}</p>}

      {data && (
        <div>
          <div className="metrics-grid">
            <div className="metric-card">
              <h2>Underlying Price</h2>
              <p>{data.current_price}</p>
            </div>
            <div className="metric-card">
              <h2>Put-Call Ratio (PCR)</h2>
              <p>{data.pcr}</p>
            </div>
            <div className="metric-card">
              <h2>Max Pain</h2>
              <p>{data.max_pain}</p>
            </div>
            <div className="metric-card">
              <h2>INDIAVIX</h2>
              <p>{data.india_vix}</p>
            </div>
          </div>

          <h2>Option Chain</h2>
          <div className="option-chain-grid">
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
  <table className="data-table">
    <thead>
      <tr>
        <th>Strike</th>
        <th>LTP</th>
        <th>IV</th>
        <th>OI</th>
        <th>OI Change</th>
        <th>Volume</th>
      </tr>
    </thead>
    <tbody>
      {options.map((option, index) => (
        <tr key={index}>
          <td>{option.strike_price}</td>
          <td>{option.ltp}</td>
          <td>{option.iv}</td>
          <td>{option.oi}</td>
          <td>{option.oi_change}</td>
          <td>{option.volume}</td>
        </tr>
      ))}
    </tbody>
  </table>
);

const FuturesTable = ({ futures }) => (
    <table className="data-table">
        <thead>
        <tr>
            <th>Expiry</th>
            <th>LTP</th>
            <th>OI</th>
            <th>OI Change</th>
            <th>Volume</th>
        </tr>
        </thead>
        <tbody>
        {futures.map((future, index) => (
            <tr key={index}>
            <td>{future.expiry}</td>
            <td>{future.ltp}</td>
            <td>{future.oi}</td>
            <td>{future.oi_change}</td>
            <td>{future.volume}</td>
            </tr>
        ))}
        </tbody>
    </table>
);

export default Dashboard;
