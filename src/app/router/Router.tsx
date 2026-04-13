import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Suspense, lazy, useEffect, useRef } from 'react';
import { LoadingOverlay } from '@mantine/core';
import { useTelegram } from '@app/providers/useTelegram';
import { MobileOnlyScreen } from '@shared/ui/MobileOnlyScreen';

// Auth pages (kept local to shell)
const AuthPage = lazy(() =>
  import('@app/pages/auth').then((m) => ({ default: m.AuthPage }))
);

// Lazy-load module routers
const UserRouter = lazy(() =>
  import('@modules/buyer/app').then((m) => ({ default: m.UserRouter }))
);
const AdminRouter = lazy(() =>
  import('@modules/admin/app').then((m) => ({ default: m.AdminRouter }))
);

function isMobileDevice(): boolean {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  );
}

// Handle Telegram Mini App deep links via start_param
function StartParamHandler() {
  const { webApp } = useTelegram();
  const navigate = useNavigate();
  const handledRef = useRef(false);

  useEffect(() => {
    if (handledRef.current) return;
    const startParam = webApp?.initDataUnsafe?.start_param;
    if (startParam?.startsWith('listing_')) {
      handledRef.current = true;
      const id = startParam.replace('listing_', '');
      navigate(`/listings/${id}`, { replace: true });
    }
  }, [webApp, navigate]);

  return null;
}

// Automatically manages Telegram's native top-bar (Back button) based on routing
function TelegramBackButtonManager() {
  const { webApp } = useTelegram();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!webApp?.BackButton) return;

    // Root paths where we only want to display "Close" natively
    const rootPaths = ['/', '/search', '/favorites', '/profile', '/auth'];
    const isRootPath = rootPaths.includes(location.pathname);

    if (!isRootPath) {
      webApp.BackButton.show();
    } else {
      webApp.BackButton.hide();
    }

    const handleBackClick = () => {
      navigate(-1);
    };

    webApp.BackButton.onClick(handleBackClick);

    return () => {
      webApp.BackButton.offClick(handleBackClick);
    };
  }, [webApp, location.pathname, navigate]);

  return null;
}

export function Router() {
  const { isTelegramWebApp, isReady } = useTelegram();

  // Show loading while checking Telegram
  if (!isReady) {
    return <LoadingOverlay visible />;
  }

  // Mobile-only guard (skip in development or when inside Telegram WebApp)
  // Allow desktop Telegram for testing
  const isDev = import.meta.env.DEV;
  if (!isDev && !isTelegramWebApp && !isMobileDevice()) {
    return <MobileOnlyScreen />;
  }

  return (
    <Suspense fallback={<LoadingOverlay visible />}>
      <StartParamHandler />
      <TelegramBackButtonManager />
      <Routes>
        {/* Auth routes (shell-level) */}
        <Route path="/auth" element={<AuthPage />} />

        {/* Admin module */}
        <Route path="/admin/*" element={<AdminRouter />} />

        {/* User module (catch-all — includes buyer + seller pages) */}
        <Route path="/*" element={<UserRouter />} />
      </Routes>
    </Suspense>
  );
}
