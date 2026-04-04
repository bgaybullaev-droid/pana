import { Routes, Route, Navigate, useParams } from "react-router-dom";
import { Suspense, lazy } from "react";
import { LoadingOverlay } from "@mantine/core";
import { Layout } from "../ui/layout";

// Lazy load buyer pages — extract .Page from { route, Page } exports
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

// Redirect component for old crawler routes
function CrawlerRedirect() {
	const { id } = useParams<{ id: string }>();
	return <Navigate to={`/listings/${id}`} replace />;
}

export function BuyerRouter() {
	return (
		<Suspense fallback={<LoadingOverlay visible />}>
			<Routes>
				{/* Routes with bottom navigation (BuyerLayout) */}
				<Route element={<Layout />}>
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
				</Route>

				{/* Full-screen pages (no bottom nav) */}
				<Route path="/listings/:id" element={<ListingDetailPage />} />
				<Route path="/seller/:id" element={<SellerProfilePage />} />
				<Route path="/browse" element={<BrowsePage />} />
			</Routes>
		</Suspense>
	);
}
