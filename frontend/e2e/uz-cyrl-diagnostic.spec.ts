import { test, expect } from "@playwright/test";

test("diagnostic — what does i18next think it is?", async ({ context, page }) => {
	await context.addInitScript(() => {
		window.localStorage.setItem("i18nextLng", "uz-cyrl");
	});
	const consoleErrors: string[] = [];
	page.on("pageerror", (e) => consoleErrors.push(e.message));
	page.on("console", (msg) => {
		if (msg.type() === "error") consoleErrors.push(msg.text());
	});
	await page.goto("/");
	await page.waitForLoadState("networkidle");

	const state = await page.evaluate(() => {
		// Access the running i18n instance via the global window if exposed,
		// otherwise via the i18next default export from the module.
		// Vite's dev server serves a singleton; try a few paths.
		// @ts-expect-error — runtime probe
		const i18n = (window as any).__i18n || (window as any).i18next || (window as any).i18n;
		if (i18n) {
			return {
				language: i18n.language,
				languages: i18n.languages,
				resolvedLanguage: i18n.resolvedLanguage,
				options: {
					fallbackLng: i18n.options?.fallbackLng,
					supportedLngs: i18n.options?.supportedLngs,
					load: i18n.options?.load,
					cleanCode: i18n.options?.cleanCode,
					nonExplicitSupportedLngs: i18n.options?.nonExplicitSupportedLngs,
				},
				stored: window.localStorage.getItem("i18nextLng"),
				resources_keys: Object.keys(i18n.store?.data || {}),
			};
		}
		return {
			stored: window.localStorage.getItem("i18nextLng"),
			i18nNotFound: true,
		};
	});

	console.log("\n========= i18next runtime state =========");
	console.log(JSON.stringify(state, null, 2));
	console.log("========= console errors =========");
	console.log(consoleErrors.slice(0, 8));
	console.log("=========================================\n");

	// At least force pass so we see the log.
	expect(true).toBe(true);
});
