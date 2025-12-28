import React from 'react';
import PCRWidget from './components/PCRWidget';
import MaxPainWidget from './components/MaxPainWidget';

const Dashboard = () => {
  return (
    <div>
      <h1>Algo Trading Dashboard</h1>
      <PCRWidget />
      <MaxPainWidget />
    </div>
  );
};

export default Dashboard;
