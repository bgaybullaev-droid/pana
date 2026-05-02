import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { BrowserRouter } from 'react-router-dom';
import { Router } from './router';
import { TelegramProvider } from './providers/TelegramProvider';
import { AuthProvider } from './providers/AuthProvider';
import { theme } from './styles/theme';

export function App() {
  return (
    <MantineProvider theme={theme} defaultColorScheme="light">
      <Notifications position="top-center" />
      <TelegramProvider>
        <BrowserRouter>
          <AuthProvider>
            <Router />
          </AuthProvider>
        </BrowserRouter>
      </TelegramProvider>
    </MantineProvider>
  );
}
