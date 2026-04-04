import { Routes, Route, Navigate } from "react-router-dom";
import { Suspense, lazy } from "react";
import { LoadingOverlay } from "@mantine/core";
import { useAuth } from "@app/providers/useAuth";
import { SellerLayout } from "../ui/layout";

// Lazy load seller pages — extract .Page from { route, Page } exports
const DashboardPage = lazy(() =>
	import("../../pages/dashboard").then((m) => ({
		default: m.SellerDashboard.Page,
	})),
);
const ListingsPage = lazy(() =>
	import("../../pages/listings").then((m) => ({
		default: m.SellerListings.Page,
	})),
);
const CrawledPage = lazy(() =>
	import("../../pages/crawled-listings").then((m) => ({
		default: m.CrawledListings.Page,
	})),
);
const CreatePage = lazy(() =>
	import("../../pages/create-listing").then((m) => ({
		default: m.CreateListing.Page,
	})),
);
const EditPage = lazy(() =>
	import("../../pages/edit-listing").then((m) => ({
		default: m.EditListing.Page,
	})),
);
const ProfilePage = lazy(() =>
	import("../../pages/profile").then((m) => ({
		default: m.SellerProfileEdit.Page,
	})),
);
const RegisterPage = lazy(() =>
	import("../../pages/register").then((m) => ({
		default: m.SellerRegister.Page,
	})),
);

function SellerRoute({ children }: { children: React.ReactNode }) {
	const { user, isLoading } = useAuth();
	if (isLoading) return <LoadingOverlay visible />;
	if (!user) return <Navigate to="/auth" replace />;
	if (!user.is_seller) return <Navigate to="/seller/register" replace />;
	return <>{children}</>;
}

export function SellerRouter() {
	return (
		<Suspense fallback={<LoadingOverlay visible />}>
			<Routes>
				<Route element={<SellerLayout />}>
					<Route
						path="dashboard"
						element={
							<SellerRoute>
								<DashboardPage />
							</SellerRoute>
						}
					/>
					<Route
						path="listings"
						element={
							<SellerRoute>
								<ListingsPage />
							</SellerRoute>
						}
					/>
					<Route
						path="crawled"
						element={
							<SellerRoute>
								<CrawledPage />
							</SellerRoute>
						}
					/>
					<Route
						path="create"
						element={
							<SellerRoute>
								<CreatePage />
							</SellerRoute>
						}
					/>
					<Route
						path="edit/:id"
						element={
							<SellerRoute>
								<EditPage />
							</SellerRoute>
						}
					/>
					<Route
						path="profile"
						element={
							<SellerRoute>
								<ProfilePage />
							</SellerRoute>
						}
					/>
					<Route path="register" element={<RegisterPage />} />
				</Route>
				<Route path="*" element={<Navigate to="dashboard" replace />} />
			</Routes>
		</Suspense>
	);
}
