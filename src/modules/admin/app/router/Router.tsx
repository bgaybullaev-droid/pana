import { Routes, Route, Navigate } from "react-router-dom";
import { Suspense, lazy } from "react";
import { LoadingOverlay } from "@mantine/core";
import { AdminLayout } from "../ui/layout";

// Lazy load admin pages — extract .Page from { route, Page } exports
const LoginPage = lazy(() =>
	import("../../pages/login").then((m) => ({ default: m.AdminLogin.Page })),
);
const DashboardPage = lazy(() =>
	import("../../pages/dashboard").then((m) => ({
		default: m.AdminDashboard.Page,
	})),
);
const UsersPage = lazy(() =>
	import("../../pages/users").then((m) => ({ default: m.AdminUsers.Page })),
);
const UserDetailPage = lazy(() =>
	import("../../pages/users").then((m) => ({ default: m.AdminUserDetailPage })),
);
const ListingsPage = lazy(() =>
	import("../../pages/listings").then((m) => ({
		default: m.AdminListings.Page,
	})),
);
const ListingDetailPage = lazy(() =>
	import("../../pages/listings").then((m) => ({
		default: m.AdminListingDetailPage,
	})),
);
const CrawledPage = lazy(() =>
	import("../../pages/crawled").then((m) => ({ default: m.AdminCrawled.Page })),
);
const CrawledDetailPage = lazy(() =>
	import("../../pages/crawled").then((m) => ({
		default: m.AdminCrawledDetailPage,
	})),
);

export function AdminRouter() {
	return (
		<Suspense fallback={<LoadingOverlay visible />}>
			<Routes>
				<Route path="login" element={<LoginPage />} />
				<Route element={<AdminLayout />}>
					<Route index element={<DashboardPage />} />
					<Route path="users" element={<UsersPage />} />
					<Route path="users/:id" element={<UserDetailPage />} />
					<Route path="listings" element={<ListingsPage />} />
					<Route path="listings/:id" element={<ListingDetailPage />} />
					<Route path="crawled" element={<CrawledPage />} />
					<Route path="crawled/:source/:id" element={<CrawledDetailPage />} />
				</Route>
				<Route path="*" element={<Navigate to="/admin" replace />} />
			</Routes>
		</Suspense>
	);
}
