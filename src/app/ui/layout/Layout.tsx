import { Outlet } from 'react-router-dom';

/**
 * Minimal shell layout — just renders child routes.
 * Module-specific layouts (BuyerLayout, SellerLayout, AdminLayout)
 * are handled within each module's own router.
 */
export function Layout() {
  return <Outlet />;
}
