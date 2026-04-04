import { Routes, Route, Navigate } from "react-router-dom";
import { Suspense, lazy } from "react";
import { Box, LoadingOverlay } from "@mantine/core";
import { useAuth } from "@app/providers/useAuth";
import { BottomNavigation } from "@modules/buyer/shared/ui/BottomNavigation";
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

/** Wrapper that shows the buyer bottom navigation on seller pages */
function WithBottomNav({ children }: { children: React.ReactNode }) {
	return (
		<Box
			style={{
				display: "flex",
				flexDirection: "column",
				height: "100%",
				width: "100%",
			}}
		>
			<Box
				style={{
					flex: 1,
					overflow: "auto",
					paddingBottom: "calc(60px + env(safe-area-inset-bottom, 0px))",
				}}
				className="hide-scrollbar"
			>
				{children}
			</Box>
			<BottomNavigation />
		</Box>
	);
}

export function SellerRouter() {
	return (
		<Suspense fallback={<LoadingOverlay visible />}>
			<Routes>
				{/* Pages with buyer bottom nav (no seller header) */}
				<Route
					path="listings"
					element={
						<SellerRoute>
							<WithBottomNav>
								<ListingsPage />
							</WithBottomNav>
						</SellerRoute>
					}
				/>
				<Route
					path="crawled"
					element={
						<SellerRoute>
							<WithBottomNav>
								<CrawledPage />
							</WithBottomNav>
						</SellerRoute>
					}
				/>
				<Route
					path="edit/:id"
					element={
						<SellerRoute>
							<WithBottomNav>
								<EditPage />
							</WithBottomNav>
						</SellerRoute>
					}
				/>

				{/* Create page — no nav at all */}
				<Route
					path="create"
					element={
						<SellerRoute>
							<CreatePage />
						</SellerRoute>
					}
				/>

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
