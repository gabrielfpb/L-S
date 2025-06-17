import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css'; // You might want to create this file
import App from './App';
import reportWebVitals from './reportWebVitals';
// import { Provider } from 'react-redux'; // Uncomment if setting up Redux immediately
// import store from './store'; // Uncomment if setting up Redux immediately

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    {/* <Provider store={store}> */}
    <App />
    {/* </Provider> */}
  </React.StrictMode>
);

reportWebVitals();
