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
// Legacy /search route — replaced by a `<Navigate>` redirect to home.
// The page module remains for now in case external links still resolve
// via the legacy bundle; remove after one deploy cycle.
const SettingsPage = lazy(() =>
	import("../../pages/settings").then((m) => ({ default: m.Settings.Page })),
);
const NotificationSettingsPage = lazy(() =>
	import("../../pages/notification-settings").then((m) => ({
		default: m.NotificationSettings.Page,
	})),
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
const SellerTariffsPage = lazy(() =>
	import("@modules/seller/pages/tariffs").then((m) => ({
		default: m.SellerTariffs.Page,
	})),
);
const SellerAutopostingPage = lazy(() =>
	import("@modules/seller/pages/autoposting").then((m) => ({
		default: m.SellerAutoposting.Page,
	})),
);
// PR-T — phase-2 referral program cabinet page.
const SellerReferralsPage = lazy(() =>
	import("@modules/seller/pages/referrals").then((m) => ({
		default: m.SellerReferrals.Page,
	})),
);
// PRU — phase-2 CRM cabinet page.
const SellerClientsPage = lazy(() =>
	import("@modules/seller/pages/clients").then((m) => ({
		default: m.SellerClients.Page,
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
					{/*
					 * Legacy /search route — the bottom-nav search button now opens
					 * the home filter drawer in place. Existing bookmarks redirect
					 * to home with the original query string preserved so the home
					 * page can hydrate filters from the URL.
					 */}
					<Route
						path="/search"
						element={<Navigate to={`/${window.location.search}`} replace />}
					/>
					<Route path="/preferences" element={<PreferencesPage />} />
					<Route path="/notification-settings" element={<NotificationSettingsPage />} />
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
					{/* C1 V2.0: tariffs are visible from day 1 — accessible
					    to prospective sellers BEFORE registration. */}
					<Route path="/seller/tariffs" element={<SellerTariffsPage />} />
					{/* Block D D4 — autoposting cabinet. SellerRoute gates entry;
					    subscription gate is enforced server-side in the API. */}
					<Route path="/seller/autoposting" element={<SellerRoute><SellerAutopostingPage /></SellerRoute>} />
					{/* PR-T — phase-2 referral program. Open to any authenticated
					    user (buyers can refer too); SellerRoute would over-restrict. */}
					<Route path="/seller/referrals" element={<SellerReferralsPage />} />
					{/* PRU — phase-2 CRM (clients pipeline). Seller-only. */}
					<Route path="/seller/clients" element={<SellerRoute><SellerClientsPage /></SellerRoute>} />
				</Route>

				{/* Full-screen pages (no bottom nav) */}
				<Route path="/listings/:id" element={<ListingDetailPage />} />
				<Route path="/seller/:id" element={<SellerProfilePage />} />
				<Route path="/browse" element={<BrowsePage />} />
				<Route path="/login" element={<Navigate to="/auth" replace />} />
				
				{/* Catch-all redirect for missing pages like /login */}
				<Route path="*" element={<Navigate to="/" replace />} />
			</Routes>
		</Suspense>
		</ErrorBoundary>
	);
}
