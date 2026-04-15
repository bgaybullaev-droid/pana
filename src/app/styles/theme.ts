import { createTheme, MantineColorsTuple } from "@mantine/core";

// Real Estate brand colors
const brandBlue: MantineColorsTuple = [
	"#e7f5ff",
	"#d0ebff",
	"#a5d8ff",
	"#74c0fc",
	"#4dabf7",
	"#40A7E3", // index 5 - primary
	"#228be6",
	"#1c7ed6",
	"#1971c2",
	"#1864ab",
];

const brandOrange: MantineColorsTuple = [
	"#fff4e6",
	"#ffe8cc",
	"#ffd8a8",
	"#ffc078",
	"#ffa94d",
	"#ff922b",
	"#FF6E01", // index 6 - accent
	"#e8590c",
	"#d9480f",
	"#c92a2a",
];

export const theme = createTheme({
	primaryColor: "blue",
	primaryShade: 5,
	colors: {
		blue: brandBlue,
		orange: brandOrange,
	},
	fontFamily:
		'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
	headings: {
		fontFamily:
			'Outfit, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
		fontWeight: "700",
	},
	defaultRadius: "lg",
	white: "#ffffff",
	black: "#1A1B1E",
	components: {
		Button: {
			defaultProps: {
				size: "md",
				radius: "md",
			},
			styles: {
				root: {
					transition: "all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1)",
					fontWeight: 600,
				},
			},
		},
		TextInput: {
			defaultProps: {
				size: "md",
				radius: "xl",
			},
			styles: {
				input: {
					border: "1.5px solid var(--mantine-color-gray-2)",
					transition: "border-color 0.2s ease, box-shadow 0.2s ease",
					"&:focus": {
						borderColor: "var(--mantine-color-blue-5)",
						boxShadow: "0 0 0 3px rgba(64, 167, 227, 0.1)",
					},
				},
			},
		},
		NumberInput: {
			defaultProps: {
				size: "md",
				radius: "xl",
			},
		},
		Select: {
			defaultProps: {
				size: "md",
				radius: "xl",
			},
		},
		Card: {
			defaultProps: {
				shadow: "none",
				radius: 12,
				withBorder: false,
			},
			styles: {
				root: {
					backgroundColor: "#fff",
					boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
					transition:
						"transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease",
					"&:active": {
						transform: "scale(0.98)",
					},
				},
			},
		},
		Badge: {
			defaultProps: {
				radius: "sm",
				fw: 600,
			},
		},
	},
});

// Utility constants for consistent usage
export const IMAGE_BASE_URL = "https://source.uchar.market/";

// ── Design tokens ──────────────────────────────────────────

export const radii = {
	sm: 8,
	md: 12,
	lg: 16,
	xl: 24,
	full: 9999,
} as const;

export const shadows = {
	sm: "0 1px 4px rgba(0,0,0,0.04)",
	md: "0 2px 12px rgba(0,0,0,0.06)",
	lg: "0 8px 32px rgba(0,0,0,0.12)",
	accent: "0 4px 12px rgba(34,139,230,0.3)",
	accentOrange: "0 4px 12px rgba(255,110,1,0.3)",
	// Legacy aliases (use new names in new code)
	card: "0 2px 12px rgba(0,0,0,0.06)",
	cardHover: "0 8px 32px rgba(0,0,0,0.12)",
	soft: "0 2px 12px rgba(0,0,0,0.06)",
	elevated: "0 8px 32px rgba(0,0,0,0.12)",
	button: "0 4px 12px rgba(34,139,230,0.3)",
} as const;

export const spacing = {
	card: 16,
	cardCompact: 12,
	page: "md" as const,
} as const;

export const surface = {
	page: "#f8f9fa",
	card: "#ffffff",
	muted: "#f1f3f5",
} as const;

export const gradients = {
	primary: "linear-gradient(135deg, #228be6, #40A7E3)",
	header: "linear-gradient(135deg, #1971c2 0%, #40A7E3 50%, #74c0fc 100%)",
	card: "linear-gradient(180deg, transparent 0%, rgba(0,0,0,0.6) 100%)",
	cardSubtle: "linear-gradient(180deg, transparent 40%, rgba(0,0,0,0.5) 100%)",
	orange: "linear-gradient(135deg, #FF6E01, #ff922b)",
} as const;

export const transitions = {
	spring: "all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1)",
	smooth: "all 0.2s ease",
	fast: "all 0.15s ease",
} as const;

// Property type color map
export const propertyTypeColors: Record<string, string> = {
	apartment: "#228be6",
	house: "#40c057",
	commercial: "#ff922b",
	land: "#be4bdb",
};

// Price formatter (locale-aware).
//
// T-020 extension: optional `period` suffix for rent listings. Two-arg calls
// keep behaving exactly as before (no suffix).
export type PricePeriod = "total" | "month" | "day";

export interface FormatPriceOptions {
	period?: PricePeriod;
}

export const formatPrice = (
	price: number,
	currency?: string,
	options?: FormatPriceOptions,
): string => {
	const lng =
		typeof window !== "undefined" && localStorage.getItem("i18nextLng");
	const locale = lng === "uz" ? "uz-Latn" : "ru-RU";
	const isUz = locale === "uz-Latn";
	// Normalize all space-like separators (NBSP U+00A0, narrow NBSP U+202F,
	// locale-specific commas) to a regular space so the output stays
	// stable across environments (JSDOM uses NBSP for ru-RU).
	const formatted = price
		.toLocaleString(locale)
		.replace(/,/g, " ")
		.replace(/[\u00A0\u202F]/g, " ");

	let base: string;
	if (!currency) {
		base = formatted;
	} else if (currency.toUpperCase() === "USD") {
		base = `$${formatted}`;
	} else {
		base = `${formatted} sum`;
	}

	const period = options?.period ?? "total";
	if (period === "total") return base;
	if (period === "month") {
		return isUz ? `${base} / oyiga` : `${base} / мес`;
	}
	// period === "day"
	return isUz ? `${base} / kuniga` : `${base} / сутки`;
};
