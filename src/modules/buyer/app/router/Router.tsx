import { Routes, Route, Navigate, useParams } from "react-router-dom";
import { Suspense, lazy } from "react";
import { LoadingOverlay } from "@mantine/core";
import { useAuth } from "@app/providers/useAuth";
import { Layout } from "../ui/layout";
import { ErrorBoundary } from "@shared/ui/ErrorBoundary";

// ── User pages (formerly "buyer") ──
const HomePage = lazy(() =>
	import("../../pages/home").then((m) => ({ default: m.Home.Page })),
);
const ListingsPage = lazy(() =>
	import("../../pages/listings").then((m) => ({ default: m.Listings.Page })),
);
const ListingDetailPage = lazy(() =>
	import("../../pages/listing-detail").then((m) => ({
		default: m.ListingDetail.Page,
	})),
);
const BrowsePage = lazy(() =>
	import("../../pages/browse").then((m) => ({ default: m.Browse.Page })),
);
const FavoritesPage = lazy(() =>
	import("../../pages/favorites").then((m) => ({ default: m.Favorites.Page })),
);
const NotificationsPage = lazy(() =>
	import("../../pages/notifications").then((m) => ({
		default: m.Notifications.Page,
	})),
);
const PreferencesPage = lazy(() =>
	import("../../pages/preferences").then((m) => ({
		default: m.Preferences.Page,
	})),
);
const BecomeSellerPage = lazy(() =>
	import("../../pages/become-seller").then((m) => ({
		default: m.BecomeSeller.Page,
	})),
);
const SellerProfilePage = lazy(() =>
	import("../../pages/seller-profile").then((m) => ({
		default: m.SellerProfile.Page,
	})),
);
const SearchPage = lazy(() =>
	import("../../pages/search").then((m) => ({ default: m.Search.Page })),
);
const SettingsPage = lazy(() =>
	import("../../pages/settings").then((m) => ({ default: m.Settings.Page })),
);
const AboutPage = lazy(() =>
	import("../../pages/about").then((m) => ({ default: m.About.Page })),
);
const ForRealtorsPage = lazy(() =>
	import("../../pages/for-realtors").then((m) => ({
		default: m.ForRealtors.Page,
	})),
);
const FAQPage = lazy(() =>
	import("../../pages/faq").then((m) => ({ default: m.FAQ.Page })),
);
const SupportPage = lazy(() =>
	import("../../pages/support").then((m) => ({ default: m.Support.Page })),
);
const PrivacyPage = lazy(() =>
	import("../../pages/privacy").then((m) => ({ default: m.Privacy.Page })),
);
const TermsPage = lazy(() =>
	import("../../pages/terms").then((m) => ({ default: m.Terms.Page })),
);
const EditProfilePage = lazy(() =>
	import("../../pages/edit-profile").then((m) => ({
		default: m.EditProfile.Page,
	})),
);

// ── Seller pages (same user, seller features) ──
const SellerDashboardPage = lazy(() =>
	import("@modules/seller/pages/dashboard").then((m) => ({
		default: m.SellerDashboard.Page,
	})),
);
const SellerListingsPage = lazy(() =>
	import("@modules/seller/pages/listings").then((m) => ({
		default: m.SellerListings.Page,
	})),
);
const SellerFoundPage = lazy(() =>
	import("@modules/seller/pages/found").then((m) => ({
		default: m.Found.Page,
	})),
);
const CreateListingPage = lazy(() =>
	import("@modules/seller/pages/create-listing").then((m) => ({
		default: m.CreateListing.Page,
	})),
);
const EditListingPage = lazy(() =>
	import("@modules/seller/pages/edit-listing").then((m) => ({
		default: m.EditListing.Page,
	})),
);
const SellerProfileEditPage = lazy(() =>
	import("@modules/seller/pages/profile").then((m) => ({
		default: m.SellerProfileEdit.Page,
	})),
);
const SellerRegisterPage = lazy(() =>
	import("@modules/seller/pages/register").then((m) => ({
		default: m.SellerRegister.Page,
	})),
);

// Auth guard for seller features
function SellerRoute({ children }: { children: React.ReactNode }) {
	const { user, isLoading } = useAuth();
	if (isLoading) return <LoadingOverlay visible />;
	if (!user) return <Navigate to="/auth" replace />;
	if (!user.is_seller) return <Navigate to="/seller/register" replace />;
	return <>{children}</>;
}

// Redirect component for old crawler routes
function CrawlerRedirect() {
	const { id } = useParams<{ id: string }>();
	return <Navigate to={`/listings/${id}`} replace />;
}

export function UserRouter() {
	return (
		<ErrorBoundary>
			<Suspense fallback={<LoadingOverlay visible />}>
				<Routes>
				{/* Routes with bottom navigation (unified layout) */}
				<Route element={<Layout />}>
					{/* ── General pages ── */}
					<Route path="/" element={<HomePage />} />
					<Route path="/search" element={<SearchPage />} />
					<Route path="/preferences" element={<PreferencesPage />} />
					<Route path="/listings" element={<ListingsPage />} />
					<Route path="/crawler/telegram/:id" element={<CrawlerRedirect />} />
					<Route path="/crawler/olx/:id" element={<CrawlerRedirect />} />
					<Route path="/notifications" element={<NotificationsPage />} />
					<Route path="/profile" element={<SettingsPage />} />
					<Route path="/become-seller" element={<BecomeSellerPage />} />
					<Route path="/favorites" element={<FavoritesPage />} />
					<Route path="/about" element={<AboutPage />} />
					<Route path="/for-realtors" element={<ForRealtorsPage />} />
					<Route path="/faq" element={<FAQPage />} />
					<Route path="/support" element={<SupportPage />} />
					<Route path="/privacy" element={<PrivacyPage />} />
					<Route path="/terms" element={<TermsPage />} />
					<Route path="/edit-profile" element={<EditProfilePage />} />

					{/* ── Seller pages (same layout, guarded) ── */}
					<Route path="/seller/register" element={<SellerRegisterPage />} />
					<Route path="/seller/dashboard" element={<SellerRoute><SellerDashboardPage /></SellerRoute>} />
					<Route path="/seller/listings" element={<SellerRoute><SellerListingsPage /></SellerRoute>} />
					<Route path="/seller/found" element={<SellerRoute><SellerFoundPage /></SellerRoute>} />
					<Route path="/seller/create" element={<SellerRoute><CreateListingPage /></SellerRoute>} />
					<Route path="/seller/edit/:id" element={<SellerRoute><EditListingPage /></SellerRoute>} />
					<Route path="/seller/profile" element={<SellerRoute><SellerProfileEditPage /></SellerRoute>} />
				</Route>

				{/* Full-screen pages (no bottom nav) */}
				<Route path="/listings/:id" element={<ListingDetailPage />} />
				<Route path="/seller/:id" element={<SellerProfilePage />} />
				<Route path="/browse" element={<BrowsePage />} />
			</Routes>
		</Suspense>
		</ErrorBoundary>
	);
}
