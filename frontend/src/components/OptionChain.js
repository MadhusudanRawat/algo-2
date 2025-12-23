import React, { useState, useEffect, useCallback } from 'react';
import { fetchOptionChain, connectToOptionChainFeed } from '../services/api';
import './OptionChain.css';

function OptionChain({ selectedExpiry }) {
  const [optionChain, setOptionChain] = useState({ calls: [], puts: [] });

  const updateLtp = useCallback((message) => {
    console.log("Received WebSocket message:", message);
    const token = message.tk;
    const ltp = message.lp;

    if (token && ltp) {
      setOptionChain(prevChain => {
        const newCalls = prevChain.calls.map(call =>
          call.token === token ? { ...call, ltp: ltp } : call
        );
        const newPuts = prevChain.puts.map(put =>
          put.token === token ? { ...put, ltp: ltp } : put
        );
        return { calls: newCalls, puts: newPuts };
      });
    }
  }, []);

  useEffect(() => {
    const getInitialData = async () => {
      const data = await fetchOptionChain("NIFTY", selectedExpiry);
      setOptionChain(data);
    };

    if (selectedExpiry) {
      getInitialData();
    }

    const closeWebSocket = connectToOptionChainFeed(updateLtp);

    return () => {
      closeWebSocket();
    };
  }, [selectedExpiry, updateLtp]);

  return (
    <div className="option-chain-container">
      <h2>Option Chain for {selectedExpiry}</h2>
      <div className="option-tables">
        <div className="option-table">
          <h3>Calls</h3>
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Strike</th>
                <th>LTP</th>
                <th>IV</th>
                <th>OI</th>
              </tr>
            </thead>
            <tbody>
              {optionChain.calls.map((call) => (
                <tr key={call.token}>
                  <td>{call.symbol}</td>
                  <td>{call.strike}</td>
                  <td>{call.ltp}</td>
                  <td>{call.iv}</td>
                  <td>{call.oi}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="option-table">
          <h3>Puts</h3>
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Strike</th>
                <th>LTP</th>
                <th>IV</th>
                <th>OI</th>
              </tr>
            </thead>
            <tbody>
              {optionChain.puts.map((put) => (
                <tr key={put.token}>
                  <td>{put.symbol}</td>
                  <td>{put.strike}</td>
                  <td>{put.ltp}</td>
                  <td>{put.iv}</td>
                  <td>{put.oi}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default OptionChain;
