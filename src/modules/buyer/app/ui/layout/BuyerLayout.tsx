import {
	useState,
	useCallback,
	useRef,
	useEffect,
	createContext,
	useContext,
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
	UnstyledButton,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useTranslation } from "react-i18next";
import { useUnit } from "effector-react";
import { IconSearch, IconX, IconClock, IconTrash } from "@tabler/icons-react";
import { BottomNavigation } from "@modules/buyer/shared/ui/BottomNavigation";
import {
	searchQueryChanged,
	applyFilters,
	$searchQuery,
} from "@modules/buyer/shared/state/model";

interface LayoutContext {
	openSearch: () => void;
	scrollRef: React.RefObject<HTMLDivElement | null>;
}

const LayoutCtx = createContext<LayoutContext>({
	openSearch: () => {},
	scrollRef: { current: null },
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
	const [searchHistory, setSearchHistory] =
		useState<string[]>(getSearchHistory);
	const activeSearchQuery = useUnit($searchQuery);

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

	// Track keyboard height — only on iOS where the viewport doesn't resize
	// for fixed/flex elements. Android handles this via 100dvh automatically.
	const isIOS =
		typeof navigator !== "undefined" &&
		/iPhone|iPad|iPod/.test(navigator.userAgent);
	const [kbHeight, setKbHeight] = useState(0);
	useEffect(() => {
		if (!searchOpen || !isIOS) {
			setKbHeight(0);
			return;
		}
		const vv = window.visualViewport;
		if (!vv) return;

		const fullHeight = window.innerHeight;
		const onResize = () => {
			const diff = Math.round(fullHeight - vv.height);
			setKbHeight(diff > 50 ? diff : 0);
		};

		vv.addEventListener("resize", onResize);
		return () => vv.removeEventListener("resize", onResize);
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
	useEffect(() => {
		const el = scrollRef.current;
		if (!el) return;

		const key = getScrollKey(location.pathname);
		const saved = sessionStorage.getItem(key);
		if (!saved) return;

		const target = parseInt(saved, 10);
		if (isNaN(target) || target <= 0) return;

		// Wait for content to render, then restore.
		// Use a polling approach: check if scroll height is sufficient,
		// retry up to ~500ms (10 × 50ms) before giving up.
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
	}, [location.pathname]);

	return (
		<LayoutCtx.Provider value={{ openSearch, scrollRef }}>
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
						paddingBottom: "calc(60px + env(safe-area-inset-bottom, 0px))",
					}}
					className="hide-scrollbar"
				>
					<Outlet />
				</Box>

				{/* Search drawer */}
				<Drawer
					opened={searchOpen}
					onClose={closeSearch}
					withCloseButton={false}
					position="bottom"
					size="100%"
					styles={{
						content: { borderRadius: 0, height: "100dvh" },
						header: { display: "none" },
						body: {
							padding: 0,
							height: "100%",
							display: "flex",
							flexDirection: "column",
						},
					}}
					zIndex={10001}
				>
					{/* Recent searches (top scrollable area) */}
					<Box style={{ flex: 1, overflow: "auto" }} px="md" pt="sm">
						{searchHistory.length > 0 && (
							<Stack gap={0}>
								<Group justify="space-between" mb={8}>
									<Text size="xs" fw={600} c="dimmed" tt="uppercase">
										{t("search.recent")}
									</Text>
									<ActionIcon
										variant="subtle"
										color="gray"
										size="sm"
										onClick={handleClearHistory}
									>
										<IconX size={14} />
									</ActionIcon>
								</Group>
								{searchHistory.map((query) => (
									<UnstyledButton
										key={query}
										onClick={() => handleHistoryClick(query)}
										style={{
											display: "flex",
											alignItems: "center",
											padding: "10px 0",
											borderBottom: "1px solid #f1f3f5",
										}}
									>
										<IconClock
											size={16}
											color="#adb5bd"
											style={{ flexShrink: 0 }}
										/>
										<Text size="sm" ml={12} style={{ flex: 1 }}>
											{query}
										</Text>
										<ActionIcon
											variant="subtle"
											color="gray"
											size="sm"
											onClick={(e) => {
												e.stopPropagation();
												handleRemoveHistory(query);
											}}
										>
											<IconTrash size={14} />
										</ActionIcon>
									</UnstyledButton>
								))}
							</Stack>
						)}

						{searchHistory.length === 0 && (
							<Box ta="center" py={48}>
								<IconSearch size={36} color="#dee2e6" stroke={1.5} />
								<Text size="sm" c="dimmed" mt={12}>
									{t("search.emptyHistory")}
								</Text>
							</Box>
						)}
					</Box>

					{/* Search input (bottom, sticks above keyboard) */}
					<Box
						px="md"
						py="sm"
						style={{
							paddingBottom:
								kbHeight > 0
									? kbHeight
									: "calc(env(safe-area-inset-bottom, 0px) + 8px)",
							borderTop: "1px solid #f1f3f5",
							flexShrink: 0,
							transition: "padding-bottom 0.1s ease-out",
						}}
					>
						<Group gap={8} wrap="nowrap">
							<TextInput
								ref={searchInputRef}
								placeholder={t("home.searchPlaceholder")}
								leftSection={<IconSearch size={18} color="#adb5bd" />}
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.currentTarget.value)}
								onKeyDown={(e) =>
									e.key === "Enter" && handleSearch(searchQuery)
								}
								autoFocus
								radius={12}
								style={{ flex: 1 }}
								styles={{
									input: {
										backgroundColor: "#f1f3f5",
										border: "none",
										height: 44,
										fontSize: 16,
									},
								}}
							/>
							<ActionIcon
								variant="subtle"
								color="gray"
								size={44}
								radius={12}
								onClick={() => {
									if (searchQuery) {
										setSearchQuery("");
									} else {
										closeSearch();
									}
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
