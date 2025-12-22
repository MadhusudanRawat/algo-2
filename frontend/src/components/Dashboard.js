import React from 'react';
import './Dashboard.css';
import ControlPanel from './ControlPanel';
import PriceDisplay from './PriceDisplay';
import OptionChain from './OptionChain';
import SignalPanel from './SignalPanel';

function Dashboard() {
  return (
    <div className="dashboard-container">
      <div className="control-panel-container">
        <ControlPanel />
      </div>
      <div className="main-content-container">
        <PriceDisplay />
        <OptionChain />
      </div>
      <div className="signal-panel-container">
        <SignalPanel />
      </div>
    </div>
  );
}

export default Dashboard;
