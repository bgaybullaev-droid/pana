import type { SectionKey } from "./requiredness";

/**
 * Smooth-scrolls to a form section by its `data-section-key` attribute.
 * A data attribute (instead of a ref registry) works uniformly across the
 * split ownership: the photos section lives in the pages while the rest
 * render inside ListingFormFields.
 */
export function scrollToSection(key: SectionKey): boolean {
	const el = document.querySelector(`[data-section-key="${key}"]`);
	if (!el) return false;
	el.scrollIntoView({ behavior: "smooth", block: "start" });
	return true;
}
