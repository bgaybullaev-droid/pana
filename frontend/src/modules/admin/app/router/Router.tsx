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
const MeiliOpsPage = lazy(() =>
	import("../../pages/meili-ops").then((m) => ({
		default: m.AdminMeiliOps.Page,
	})),
);
const AuditLogPage = lazy(() =>
	import("../../pages/audit-log").then((m) => ({
		default: m.AdminAuditLog.Page,
	})),
);
const ListingEditPage = lazy(() =>
	import("../../pages/listing-edit").then((m) => ({
		default: m.AdminListingEdit.Page,
	})),
);
const SourcesPage = lazy(() =>
	import("../../pages/sources").then((m) => ({ default: m.AdminSources.Page })),
);
const AIQualityPage = lazy(() =>
	import("../../pages/ai-quality").then((m) => ({
		default: m.AdminAIQuality.Page,
	})),
);
const SynonymsPage = lazy(() =>
	import("../../pages/synonyms").then((m) => ({
		default: m.AdminSynonyms.Page,
	})),
);
const ExportTemplatesPage = lazy(() =>
	import("../../pages/export-templates").then((m) => ({
		default: m.AdminExportTemplates.Page,
	})),
);
const AnalyticsPage = lazy(() =>
	import("../../pages/analytics").then((m) => ({
		default: m.AdminAnalytics.Page,
	})),
);
const BannersPage = lazy(() =>
	import("../../pages/banners").then((m) => ({
		default: m.AdminBanners.Page,
	})),
);
const SuspicionsPage = lazy(() =>
	import("../../pages/suspicions").then((m) => ({
		default: m.AdminSuspicions.Page,
	})),
);
const BotLimitsPage = lazy(() =>
	import("../../pages/bot-limits").then((m) => ({
		default: m.AdminBotLimits.Page,
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
					<Route path="listings/:id/edit" element={<ListingEditPage />} />
					<Route path="crawled" element={<CrawledPage />} />
					<Route path="crawled/:source/:id" element={<CrawledDetailPage />} />
					<Route path="sources" element={<SourcesPage />} />
					<Route path="ai-quality" element={<AIQualityPage />} />
					<Route path="synonyms" element={<SynonymsPage />} />
					<Route path="export-templates" element={<ExportTemplatesPage />} />
					<Route path="analytics" element={<AnalyticsPage />} />
					<Route path="banners" element={<BannersPage />} />
					<Route path="suspicions" element={<SuspicionsPage />} />
					<Route path="bot-limits" element={<BotLimitsPage />} />
					<Route path="ops/meili" element={<MeiliOpsPage />} />
					<Route path="audit" element={<AuditLogPage />} />
				</Route>
				<Route path="*" element={<Navigate to="/admin" replace />} />
			</Routes>
		</Suspense>
	);
}
