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
				radius: "md",
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
		Select: {
			defaultProps: {
				size: "md",
				radius: "md",
			},
		},
		Card: {
			defaultProps: {
				shadow: "none",
				radius: 16,
				withBorder: false,
			},
			styles: {
				root: {
					backgroundColor: "#fff",
					boxShadow: "0 2px 8px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06)",
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

// Design tokens
export const shadows = {
	card: "0 2px 8px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06)",
	cardHover: "0 4px 12px rgba(0,0,0,0.06), 0 12px 32px rgba(0,0,0,0.1)",
	soft: "0 2px 12px rgba(0,0,0,0.06)",
	elevated: "0 8px 32px rgba(0,0,0,0.12)",
	button: "0 4px 12px rgba(34,139,230,0.3)",
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

// Price formatter (locale-aware)
export const formatPrice = (price: number, currency?: string): string => {
	const lng =
		typeof window !== "undefined" && localStorage.getItem("i18nextLng");
	const locale = lng === "uz" ? "uz-Latn" : "ru-RU";
	const formatted = price.toLocaleString(locale).replace(/,/g, " ");
	if (!currency) return formatted;
	if (currency.toUpperCase() === "USD") return `$${formatted}`;
	return `${formatted} sum`;
};
