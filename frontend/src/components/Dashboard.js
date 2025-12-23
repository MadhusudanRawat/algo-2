import React, { useState } from 'react';
import './Dashboard.css';
import ControlPanel from './ControlPanel';
import PriceDisplay from './PriceDisplay';
import OptionChain from './OptionChain';
import SignalPanel from './SignalPanel';

function Dashboard() {
  const expiryDates = ["25JUL2024", "01AUG2024", "08AUG2024"]; // Example dates
  const [selectedExpiry, setSelectedExpiry] = useState(expiryDates[0]);

  return (
    <div className="dashboard-container">
      <div className="control-panel-container">
        <ControlPanel
          expiryDates={expiryDates}
          selectedExpiry={selectedExpiry}
          onExpiryChange={setSelectedExpiry}
        />
      </div>
      <div className="main-content-container">
        <PriceDisplay />
        <OptionChain selectedExpiry={selectedExpiry} />
      </div>
      <div className="signal-panel-container">
        <SignalPanel />
      </div>
    </div>
  );
}

export default Dashboard;
