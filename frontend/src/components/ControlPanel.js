import React from 'react';

function ControlPanel({ expiryDates, selectedExpiry, onExpiryChange }) {
  return (
    <div className="control-panel">
      <h2>Control Panel</h2>
      <div className="form-group">
        <label htmlFor="expiry-date">Expiry Date:</label>
        <select
          id="expiry-date"
          value={selectedExpiry}
          onChange={(e) => onExpiryChange(e.target.value)}
        >
          {expiryDates.map((date) => (
            <option key={date} value={date}>
              {date}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

export default ControlPanel;
