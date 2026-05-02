import '@shared/i18n';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from '@app/index';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import 'swiper/css';
import 'swiper/css/effect-creative';
import 'swiper/css/virtual';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
