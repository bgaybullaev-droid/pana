import {
	useState,
	useCallback,
	useRef,
	useEffect,
	useMemo,
	createContext,
	useContext,
	Suspense,
} from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
	ActionIcon,
	Box,
	Drawer,
	Group,
	Stack,
	Text,
	TextInput,
	ThemeIcon,
	UnstyledButton,
	LoadingOverlay,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useTranslation } from "react-i18next";
import { useUnit } from "effector-react";
import {
	IconSearch,
	IconX,
	IconClock,
	IconCheck,
	IconBulb,
} from "@tabler/icons-react";
import { BottomNavigation } from "@modules/buyer/shared/ui/BottomNavigation";
import {
	searchQueryChanged,
	applyFilters,
	$searchQuery,
} from "@modules/buyer/shared/state/model";
import { radii, shadows, surface } from "@app/styles/theme";
import {
	REGIONS,
	translateRegion,
	translateDistrict,
} from "@shared/lib/regions";

interface LayoutContext {
	openSearch: () => void;
	searchOpen: boolean;
	scrollRef: React.RefObject<HTMLDivElement | null>;
	headerVisible: boolean;
}

const LayoutCtx = createContext<LayoutContext>({
	openSearch: () => {},
	searchOpen: false,
	scrollRef: { current: null },
	headerVisible: true,
});
export const useLayoutContext = () => useContext(LayoutCtx);

const SCROLL_KEY_PREFIX = "scroll_pos_";

export function getScrollKey(pathname: string) {
	return `${SCROLL_KEY_PREFIX}${pathname}`;
}

export function clearScrollPosition(pathname: string) {
	sessionStorage.removeItem(getScrollKey(pathname));
}

const SEARCH_HISTORY_KEY = "uchar_search_history";
const MAX_HISTORY = 10;

function getSearchHistory(): string[] {
	try {
		const raw = localStorage.getItem(SEARCH_HISTORY_KEY);
		return raw ? JSON.parse(raw) : [];
	} catch {
		return [];
	}
}

function saveSearchHistory(history: string[]) {
	localStorage.setItem(
		SEARCH_HISTORY_KEY,
		JSON.stringify(history.slice(0, MAX_HISTORY)),
	);
}

export function Layout() {
	const { t } = useTranslation("buyer");
	const navigate = useNavigate();
	const location = useLocation();
	const scrollRef = useRef<HTMLDivElement | null>(null);
	const [searchOpen, { close: closeSearchRaw, open: openSearchDrawer }] =
		useDisclosure(false);

	const closeSearch = useCallback(() => {
		// Blur active element to dismiss mobile keyboard immediately
		if (document.activeElement instanceof HTMLElement) {
			document.activeElement.blur();
		}
		closeSearchRaw();
	}, [closeSearchRaw]);
	const searchInputRef = useRef<HTMLInputElement>(null);
	const [searchQuery, setSearchQuery] = useState("");
	const [searchFocused, setSearchFocused] = useState(false);
	const [searchHistory, setSearchHistory] =
		useState<string[]>(getSearchHistory);
	const activeSearchQuery = useUnit($searchQuery);
	const [headerVisible, setHeaderVisible] = useState(true);
	const lastScrollY = useRef(0);
	const scrollTicking = useRef(false);

	// --- Header Visibility Scroll Tracker ---
	useEffect(() => {
		const el = scrollRef.current;
		if (!el) return;

		const handleScroll = () => {
			if (!scrollTicking.current) {
				window.requestAnimationFrame(() => {
					const currentScrollY = el.scrollTop;
					const delta = currentScrollY - lastScrollY.current;

					// iOS bounce protection: ignore scrolls above top
					if (currentScrollY <= 0) {
						setHeaderVisible(true);
						lastScrollY.current = 0;
						scrollTicking.current = false;
						return;
					}

					// Standard logic: hide on scroll down (threshold 60px), show on scroll up
					if (delta > 15 && currentScrollY > 80) {
						setHeaderVisible(false);
					} else if (delta < -20 || currentScrollY <= 40) {
						setHeaderVisible(true);
					}

					lastScrollY.current = currentScrollY;
					scrollTicking.current = false;
				});
				scrollTicking.current = true;
			}
		};

		el.addEventListener("scroll", handleScroll, { passive: true });
		return () => el.removeEventListener("scroll", handleScroll);
	}, [location.pathname]);

	// Build search suggestions from districts, property types, deal types
	const searchSuggestions = useMemo(() => {
		if (!searchQuery || searchQuery.length < 2) return [];
		const q = searchQuery.toLowerCase();
		const results: string[] = [];

		// Property types
		const propertyTypes = ["apartment", "house", "commercial", "land"] as const;
		for (const pt of propertyTypes) {
			const label = t(`common.propertyType.${pt}`);
			if (label.toLowerCase().includes(q)) {
				results.push(label);
			}
		}

		// Deal types
		const dealLabels = [t("common.buy"), t("common.rent")];
		for (const dl of dealLabels) {
			if (dl.toLowerCase().includes(q)) results.push(dl);
		}

		// Districts
		for (const region of REGIONS) {
			const regionName = translateRegion(region.key, t);
			if (regionName.toLowerCase().includes(q)) {
				results.push(regionName);
			}
			for (const district of region.districts) {
				const districtName = translateDistrict(district, t);
				if (districtName.toLowerCase().includes(q)) {
					results.push(districtName);
					// Also add combos: "квартира Юнусабадский р-н"
					for (const pt of propertyTypes) {
						const ptLabel = t(`common.propertyType.${pt}`);
						results.push(`${ptLabel} ${districtName}`);
					}
				}
			}
		}

		// Deduplicate, exclude exact match with query, limit to 6
		const unique = [...new Set(results)]
			.filter((r) => r.toLowerCase() !== q)
			.slice(0, 6);
		return unique;
	}, [searchQuery, t]);

	const openSearch = useCallback(() => {
		setSearchQuery(activeSearchQuery);

		// iOS trick: create a temporary invisible input and focus it synchronously
		// within the user gesture. This "primes" iOS to allow keyboard opening.
		// Later, when the real input mounts, we transfer focus to it.
		const isIOS = /iPhone|iPad|iPod/.test(navigator.userAgent);
		if (isIOS) {
			const tmp = document.createElement("input");
			tmp.style.position = "fixed";
			tmp.style.top = "50%";
			tmp.style.left = "0";
			tmp.style.opacity = "0";
			tmp.style.height = "0";
			tmp.style.fontSize = "16px"; // prevent iOS zoom
			document.body.appendChild(tmp);
			tmp.focus();
			// Remove after the real input takes focus
			setTimeout(() => {
				if (document.body.contains(tmp)) {
					document.body.removeChild(tmp);
				}
			}, 600);
		}

		openSearchDrawer();
	}, [activeSearchQuery, openSearchDrawer]);

	// Focus the search input when drawer opens.
	useEffect(() => {
		if (!searchOpen) return;
		const timers = [50, 150, 300, 500].map((delay) =>
			setTimeout(() => {
				if (searchInputRef.current) {
					searchInputRef.current.focus();
				}
			}, delay),
		);
		return () => timers.forEach(clearTimeout);
	}, [searchOpen]);

	// iOS keyboard: resize the drawer to match the visual viewport.
	// On iOS, the layout viewport stays full-size when the keyboard opens,
	// but the visual viewport shrinks. We track it and set the drawer
	// height + offset so the content (and bottom input) stay visible.
	// Android handles this via 100dvh automatically.
	const isIOS =
		typeof navigator !== "undefined" &&
		/iPhone|iPad|iPod/.test(navigator.userAgent);
	const [vvStyle, setVvStyle] = useState<React.CSSProperties>({});
	useEffect(() => {
		if (!searchOpen || !isIOS) {
			setVvStyle({});
			return;
		}
		const vv = window.visualViewport;
		if (!vv) return;

		const update = () => {
			setVvStyle({
				height: `${vv.height}px`,
				transform: `translateY(${vv.offsetTop}px)`,
			});
		};

		// Initial sync
		update();

		vv.addEventListener("resize", update);
		vv.addEventListener("scroll", update);
		return () => {
			vv.removeEventListener("resize", update);
			vv.removeEventListener("scroll", update);
		};
	}, [searchOpen, isIOS]);

	// Scroll focused inputs into view inside drawers (Layer 2)
	useEffect(() => {
		const onFocusIn = (e: FocusEvent) => {
			const target = e.target;
			if (
				!(
					target instanceof HTMLInputElement ||
					target instanceof HTMLTextAreaElement
				)
			)
				return;
			// Skip the search input — handled by keyboard height offset
			if (target === searchInputRef.current) return;
			// Only handle inputs inside drawers/modals
			if (!target.closest('[role="dialog"], .mantine-Drawer-content')) return;
			setTimeout(() => {
				target.scrollIntoView({ behavior: "smooth", block: "center" });
			}, 300);
		};
		document.addEventListener("focusin", onFocusIn);
		return () => document.removeEventListener("focusin", onFocusIn);
	}, []);

	const handleSearch = useCallback(
		(query: string) => {
			const trimmed = query.trim();
			if (!trimmed) return;
			// Add to history (deduplicate, most recent first)
			const updated = [
				trimmed,
				...searchHistory.filter((h) => h !== trimmed),
			].slice(0, MAX_HISTORY);
			setSearchHistory(updated);
			saveSearchHistory(updated);
			setSearchQuery("");
			closeSearch();
			// Use Effector events to trigger search directly (home page may already be mounted)
			clearScrollPosition("/");
			searchQueryChanged(trimmed);
			applyFilters();
			navigate("/");
		},
		[searchHistory, closeSearch, navigate],
	);

	const handleHistoryClick = useCallback(
		(query: string) => {
			handleSearch(query);
		},
		[handleSearch],
	);

	const handleRemoveHistory = useCallback(
		(query: string) => {
			const updated = searchHistory.filter((h) => h !== query);
			setSearchHistory(updated);
			saveSearchHistory(updated);
		},
		[searchHistory],
	);

	const handleClearHistory = useCallback(() => {
		setSearchHistory([]);
		saveSearchHistory([]);
	}, []);

	// --- Scroll position save (throttled) ---
	useEffect(() => {
		const el = scrollRef.current;
		if (!el) return;

		let ticking = false;
		const handleScroll = () => {
			if (ticking) return;
			ticking = true;
			requestAnimationFrame(() => {
				if (scrollRef.current) {
					sessionStorage.setItem(
						getScrollKey(location.pathname),
						String(scrollRef.current.scrollTop),
					);
				}
				ticking = false;
			});
		};

		el.addEventListener("scroll", handleScroll, { passive: true });
		return () => el.removeEventListener("scroll", handleScroll);
	}, [location.pathname]);

	// --- Scroll position restore on route change ---
	// Only restore scroll for root tabs; inner pages always start at top.
	const ROOT_TABS = ["/", "/favorites", "/profile"];

	useEffect(() => {
		const el = scrollRef.current;
		if (!el) return;

		// Inner pages: always scroll to top
		if (!ROOT_TABS.includes(location.pathname)) {
			el.scrollTop = 0;
			return;
		}

		// Root tabs: restore saved position
		const key = getScrollKey(location.pathname);
		const saved = sessionStorage.getItem(key);
		if (!saved) return;

		const target = parseInt(saved, 10);
		if (isNaN(target) || target <= 0) return;

		let attempts = 0;
		const maxAttempts = 10;

		const tryRestore = () => {
			if (!scrollRef.current) return;
			if (
				scrollRef.current.scrollHeight >=
				target + scrollRef.current.clientHeight * 0.5
			) {
				scrollRef.current.scrollTop = target;
				return;
			}
			attempts++;
			if (attempts < maxAttempts) {
				requestAnimationFrame(tryRestore);
			}
		};

		requestAnimationFrame(tryRestore);
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [location.pathname]);

	return (
		<LayoutCtx.Provider value={{ openSearch, searchOpen, scrollRef, headerVisible }}>
			<Box
				style={{
					display: "flex",
					flexDirection: "column",
					height: "100%",
					width: "100%",
				}}
			>
				{/* Main content area */}
				<Box
					ref={scrollRef}
					style={{
						flex: 1,
						overflow: "auto",
						paddingBottom: "calc(60px + var(--safe-area-inset-bottom))",
					}}
					className="hide-scrollbar"
				>
					<Box style={{ maxWidth: 980, margin: "0 auto", width: "100%", position: "relative", minHeight: "100%" }}>
						<Suspense fallback={<LoadingOverlay visible />}>
							<Outlet />
						</Suspense>
					</Box>
				</Box>

				{/* Search drawer */}
				<Drawer
					opened={searchOpen}
					onClose={closeSearch}
					withCloseButton={false}
					position="bottom"
					size="100%"
					styles={{
						content: {
							borderRadius: 0,
							height: "100dvh",
							overflow: "hidden",
						},
						header: { display: "none" },
						body: {
							padding: 0,
							height: "100%",
							display: "flex",
							flexDirection: "column",
							...(isIOS ? vvStyle : {}),
							position: isIOS ? "fixed" : undefined,
							top: isIOS ? 0 : undefined,
							left: isIOS ? 0 : undefined,
							right: isIOS ? 0 : undefined,
							willChange: isIOS ? "transform, height" : undefined,
						},
					}}
					zIndex={10001}
				>
					{/* Scrollable area — top padding clears the fullscreen system zone */}
					<Box
						style={{
							flex: 1,
							overflowY: "auto",
							maxWidth: 980,
							margin: "0 auto",
							width: "100%",
							paddingTop: "calc(var(--app-top-inset) + 16px)",
						}}
						px="md"
					>
						{/* History — filtered by current query, in a card */}
						{(() => {
							const filtered = searchQuery
								? searchHistory.filter((q) => q.toLowerCase().includes(searchQuery.toLowerCase()))
								: searchHistory;
							return filtered.length > 0 ? (
								<Box
									mb="md"
									style={{
										backgroundColor: surface.card,
										borderRadius: radii.lg,
										border: "1px solid #e9ecef",
										boxShadow: shadows.sm,
										padding: "12px 14px",
									}}
								>
									<Group justify="space-between" mb={10}>
										<Text size="sm" fw={700} c="dark">
											{t("search.youSearched")}
										</Text>
										{!searchQuery && (
											<UnstyledButton onClick={handleClearHistory}>
												<Text size="sm" c="dimmed">
													{t("search.clearAll")}
												</Text>
											</UnstyledButton>
										)}
									</Group>
									<Group gap={8} wrap="wrap">
										{filtered.map((query) => (
											<UnstyledButton
												key={query}
												onClick={() => handleHistoryClick(query)}
												style={{
													display: "flex",
													alignItems: "center",
													gap: 6,
													padding: "6px 12px 6px 10px",
													borderRadius: radii.full,
													backgroundColor: surface.muted,
													border: "1px solid #e9ecef",
												}}
											>
												<IconClock size={14} color="#adb5bd" />
												<Text size="sm" c="dark.4">
													{query}
												</Text>
												<ActionIcon
													component="span"
													variant="transparent"
													size={16}
													onClick={(e) => {
														e.stopPropagation();
														handleRemoveHistory(query);
													}}
													style={{ marginLeft: 2 }}
												>
													<IconX size={12} color="#adb5bd" />
												</ActionIcon>
											</UnstyledButton>
										))}
									</Group>
								</Box>
							) : null;
						})()}

						{/* Suggestions — shown when typing */}
						{searchQuery && searchSuggestions.length > 0 && (
							<Box
								style={{
									backgroundColor: surface.card,
									borderRadius: radii.lg,
									border: "1px solid #e9ecef",
									boxShadow: shadows.sm,
									overflow: "hidden",
								}}
							>
								{searchSuggestions.map((suggestion, i) => (
									<UnstyledButton
										key={suggestion}
										onClick={() => handleSearch(suggestion)}
										style={{
											display: "flex",
											alignItems: "center",
											gap: 12,
											padding: "12px 14px",
											width: "100%",
											borderTop: i > 0 ? "1px solid #f1f3f5" : "none",
										}}
									>
										<IconSearch size={16} color="#adb5bd" style={{ flexShrink: 0 }} />
										<Text size="sm" c="dark.6">
											{suggestion}
										</Text>
									</UnstyledButton>
								))}
							</Box>
						)}

						{/* Onboarding — shown only when no history and no query */}
						{!searchQuery && searchHistory.length === 0 && (
							<Stack gap="md" pt="sm">
								<Box ta="center" px="md">
									<Text fw={700} size="xl" c="dark" mb={6}>
										{t("search.onboarding.title")}
									</Text>
									<Text size="sm" c="dimmed" lh={1.5}>
										{t("search.onboarding.subtitle")}
									</Text>
								</Box>

								<Stack gap={10}>
									{(["market", "nodup", "alerts"] as const).map((key) => (
										<Box
											key={key}
											style={{
												backgroundColor: surface.page,
												borderRadius: radii.md,
												padding: "14px 16px",
												display: "flex",
												alignItems: "center",
												gap: 14,
											}}
										>
											<ThemeIcon
												size={32}
												radius="50%"
												variant="light"
												color="blue"
												style={{ flexShrink: 0 }}
											>
												<IconCheck size={16} />
											</ThemeIcon>
											<Box>
												<Text size="sm" fw={700} c="dark">
													{t(`search.onboarding.features.${key}.title`)}
												</Text>
												<Text size="xs" c="dimmed" mt={2}>
													{t(`search.onboarding.features.${key}.desc`)}
												</Text>
											</Box>
										</Box>
									))}
								</Stack>

								<Box
									style={{
										backgroundColor: "#fff9db",
										borderRadius: radii.md,
										padding: "12px 14px",
										display: "flex",
										alignItems: "flex-start",
										gap: 10,
										border: "1px solid #ffe066",
									}}
								>
									<IconBulb
										size={16}
										color="#f59f00"
										style={{ marginTop: 2, flexShrink: 0 }}
									/>
									<Text size="xs" c="dark.4" lh={1.5}>
										{t("search.onboarding.tip")}
									</Text>
								</Box>
							</Stack>
						)}
					</Box>

					{/* Search input (bottom, sticks above keyboard) */}
					<Box
						px="md"
						py="sm"
						style={{
							paddingBottom: "calc(var(--safe-area-inset-bottom) + 8px)",
							borderTop: "1px solid #f1f3f5",
							flexShrink: 0,
							maxWidth: 980,
							margin: "0 auto",
							width: "100%",
						}}
					>
						<Group gap={8} wrap="nowrap">
							<TextInput
								ref={searchInputRef}
								placeholder={searchFocused ? "" : t("search.title")}
								leftSection={<IconSearch size={18} color="#adb5bd" />}
								rightSection={
									searchQuery ? (
										<ActionIcon
											variant="filled"
											size={18}
											radius="50%"
											color="gray.5"
											onClick={() => setSearchQuery("")}
										>
											<IconX size={10} color="white" />
										</ActionIcon>
									) : null
								}
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.currentTarget.value)}
								onKeyDown={(e) =>
									e.key === "Enter" && handleSearch(searchQuery)
								}
								enterKeyHint="search"
								autoFocus
								radius={radii.xl}
								style={{ flex: 1 }}
								onFocus={() => setSearchFocused(true)}
								onBlur={() => setSearchFocused(false)}
								styles={{
									input: {
										backgroundColor: "#ffffff",
										border: "1px solid #dee2e6",
										height: 45,
										fontSize: 16,
										transition:
											"background-color 0.15s ease, border-color 0.15s ease",
									},
								}}
							/>
							<ActionIcon
								variant="subtle"
								color="gray"
								size={45}
								radius="50%"
								style={{
									backgroundColor: "#ffffff",
									border: "1px solid #dee2e6",
									transition:
										"background-color 0.15s ease, border-color 0.15s ease",
									flexShrink: 0,
								}}
								onClick={() => {
									setSearchQuery("");
									closeSearch();
								}}
							>
								<IconX size={20} />
							</ActionIcon>
						</Group>
					</Box>
				</Drawer>

				{/* Bottom navigation */}
				<BottomNavigation
					onSearchToggle={searchOpen ? closeSearch : openSearch}
					searchOpen={searchOpen}
				/>
			</Box>
		</LayoutCtx.Provider>
	);
}
