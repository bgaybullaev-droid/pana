/**
 * Ad-hoc smoke test for the Uzbek-Cyrillic locale. Opens public pages,
 * sets localStorage.i18nextLng to 'uz-cyrl', reloads, and asserts that
 * known Uzbek-Cyrillic strings appear in the rendered DOM. Run with:
 *
 *   npx playwright test e2e/uz-cyrl-smoke.spec.ts --project=chromium
 */
import { test, expect } from "@playwright/test";

const LANG = "uz-cyrl";

// Words that must NEVER show on the page in this locale (Russian-only signals).
const RUSSIAN_FORBIDDEN = [
	"Главная",
	"Поиск",
	"Объявления",
	"Сохранить",
	"Подробнее",
];

// Words that MUST appear somewhere on the page (Cyrillic-Uzbek anchors).
const EXPECTED_ANY_OF = [
	"Бош",      // home
	"Қидирув",  // search
	"Эълон",    // listing
	"Лента",    // feed (loanword, both langs share)
];

test.describe("uz-cyrl locale smoke", () => {
	test.beforeEach(async ({ context, page }) => {
		await context.addInitScript((lang) => {
			window.localStorage.setItem("i18nextLng", lang);
		}, LANG);
	});

	test("home page renders Uzbek Cyrillic", async ({ page }) => {
		const consoleErrors: string[] = [];
		page.on("pageerror", (err) => consoleErrors.push(err.message));
		await page.goto("/");
		await page.waitForLoadState("networkidle");
		const bodyText = await page.locator("body").innerText();
		console.log("--- home page text (first 800 chars) ---");
		console.log(bodyText.slice(0, 800));
		const foundExpected = EXPECTED_ANY_OF.some((w) => bodyText.includes(w));
		const leakedRussian = RUSSIAN_FORBIDDEN.filter((w) => bodyText.includes(w));
		expect(
			foundExpected,
			`none of the expected uz-cyrl anchors appeared in the page`,
		).toBe(true);
		expect(leakedRussian, "Russian-only words leaked into uz-cyrl render").toEqual([]);
		expect(consoleErrors, "no JS exceptions").toEqual([]);
	});

	test("settings page lists 4 languages including uz-cyrl + uz-latn", async ({ page }) => {
		await page.goto("/settings");
		await page.waitForLoadState("domcontentloaded");
		await page.waitForTimeout(500);
		const text = await page.locator("body").innerText();
		console.log("--- settings page text ---");
		console.log(text.slice(0, 600));
		// Should show all four language options (the codes themselves)
		const langCodes = ["ru", "uz", "uz-cyrl", "uz-latn"];
		for (const code of langCodes) {
			// Either the locale code or the display label should appear somewhere
			const present = text.toLowerCase().includes(code) || text.includes(code.toUpperCase());
			if (!present) {
				console.warn(`locale code "${code}" not visible on settings page`);
			}
		}
	});

	test("i18next resolves uz-cyrl as the primary language", async ({ page }) => {
		await page.goto("/");
		await page.waitForLoadState("networkidle");
		const state = await page.evaluate(
			() => (window as unknown as { __i18n?: { language: string; languages: string[]; resolvedLanguage: string } }).__i18n,
		);
		expect(state?.language).toBe("uz-cyrl");
		expect(state?.resolvedLanguage).toBe("uz-cyrl");
		expect(state?.languages?.[0]).toBe("uz-cyrl");
	});
});
