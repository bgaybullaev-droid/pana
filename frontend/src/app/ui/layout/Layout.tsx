import { Outlet } from 'react-router-dom';

/**
 * Minimal shell layout — just renders child routes.
 * UserLayout (bottom nav, search, scroll) wraps user routes.
 * AdminLayout wraps admin routes separately.
 */
export function Layout() {
  return <Outlet />;
}
