import React from 'react';
import PCRWidget from './components/PCRWidget';
import MaxPainWidget from './components/MaxPainWidget';
import StraddleDashboard from './components/StraddleDashboard';

const Dashboard = () => {
  return (
    <div>
      <h1>Algo Trading Dashboard</h1>
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:16}}>
        <div>
          <PCRWidget />
          <MaxPainWidget />
        </div>
        <div>
          <StraddleDashboard />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
