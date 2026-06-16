import { useLocation, useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import {
	IconLayoutDashboard,
	IconUsers,
	IconList,
	IconWorldSearch,
	IconServerCog,
	IconHistory,
	IconBroadcast,
	IconSparkles,
	IconLanguage,
	IconFileExport,
	IconChartLine,
	IconPhoto,
	IconShieldExclamation,
	IconGauge,
	IconReportSearch,
} from "@tabler/icons-react";
import { $dashboardStats } from "@modules/admin/shared/state";

export interface NavItem {
	icon: typeof IconLayoutDashboard;
	labelKey: string;
	path: string;
	badgeKey?: "pending_users" | "pending_listings";
}

export const NAV_ITEMS: NavItem[] = [
	{
		icon: IconLayoutDashboard,
		labelKey: "nav.dashboard",
		path: "/admin",
	},
	{
		icon: IconUsers,
		labelKey: "nav.users",
		path: "/admin/users",
		badgeKey: "pending_users",
	},
	{
		icon: IconList,
		labelKey: "nav.listings",
		path: "/admin/listings",
		badgeKey: "pending_listings",
	},
	{
		icon: IconWorldSearch,
		labelKey: "nav.crawled",
		path: "/admin/crawled",
	},
	{
		icon: IconBroadcast,
		labelKey: "nav.sources",
		path: "/admin/sources",
	},
	{
		icon: IconSparkles,
		labelKey: "nav.aiQuality",
		path: "/admin/ai-quality",
	},
	{
		icon: IconLanguage,
		labelKey: "nav.synonyms",
		path: "/admin/synonyms",
	},
	{
		icon: IconFileExport,
		labelKey: "nav.exportTemplates",
		path: "/admin/export-templates",
	},
	{
		icon: IconChartLine,
		labelKey: "nav.analytics",
		path: "/admin/analytics",
	},
	{
		icon: IconPhoto,
		labelKey: "nav.banners",
		path: "/admin/banners",
	},
	{
		icon: IconShieldExclamation,
		labelKey: "nav.suspicions",
		path: "/admin/suspicions",
	},
	{
		icon: IconGauge,
		labelKey: "nav.botLimits",
		path: "/admin/bot-limits",
	},
	{
		icon: IconReportSearch,
		labelKey: "nav.searchTelemetry",
		path: "/admin/search-telemetry",
	},
	{
		icon: IconServerCog,
		labelKey: "nav.meiliOps",
		path: "/admin/ops/meili",
	},
	{
		icon: IconHistory,
		labelKey: "nav.auditLog",
		path: "/admin/audit",
	},
];

export interface ResolvedNavItem extends NavItem {
	isActive: boolean;
	badgeCount: number;
	label: string;
}

/**
 * Single source of truth for the admin navigation: resolves each NAV_ITEM into
 * its active state, badge count and translated label. Reused by the desktop
 * sidebar (full + rail) and the mobile drawer so they never drift apart.
 */
export function useAdminNav() {
	const location = useLocation();
	const navigate = useNavigate();
	const [stats] = useUnit([$dashboardStats]);
	const { t } = useTranslation("admin");

	const items: ResolvedNavItem[] = NAV_ITEMS.map((item) => ({
		...item,
		isActive:
			item.path === "/admin"
				? location.pathname === "/admin"
				: location.pathname.startsWith(item.path),
		badgeCount: item.badgeKey && stats ? stats[item.badgeKey] : 0,
		label: t(item.labelKey),
	}));

	return { items, navigate };
}
