/**
 * Cross-script fuzzy search normalization for Uzbek/Russian autocomplete.
 *
 * Handles the most common mismatches:
 *  1. A/O phonetic variation between Russian and Uzbek Cyrillic
 *     ("АКЛАМ" vs "ОКЛАМ", "Олмазор" vs "Алмазар")
 *  2. Latin input when the UI is in Cyrillic ("Chilonzor" → "Чиланзор")
 *  3. Apostrophe removal from Uzbek Latin ("o'", "g'", "O'")
 */

const LATN_TO_CYRL: [string, string][] = [
	["ch", "ч"],
	["sh", "ш"],
	["ts", "ц"],
	["zh", "ж"],
	["yo", "ё"],
	["yu", "ю"],
	["ya", "я"],
	["a", "а"],
	["b", "б"],
	["d", "д"],
	["e", "э"],
	["f", "ф"],
	["g", "г"],
	["h", "х"],
	["i", "и"],
	["j", "й"],
	["k", "к"],
	["l", "л"],
	["m", "м"],
	["n", "н"],
	["o", "о"],
	["p", "п"],
	["q", "қ"],
	["r", "р"],
	["s", "с"],
	["t", "т"],
	["u", "у"],
	["v", "в"],
	["w", "в"],
	["x", "х"],
	["y", "й"],
	["z", "з"],
];

function transliterateLatnToCyrl(text: string): string {
	let result = "";
	let i = 0;
	while (i < text.length) {
		let matched = false;
		for (const [latn, cyrl] of LATN_TO_CYRL) {
			if (text.startsWith(latn, i)) {
				result += cyrl;
				i += latn.length;
				matched = true;
				break;
			}
		}
		if (!matched) {
			result += text[i];
			i++;
		}
	}
	return result;
}

function normalizeBase(text: string): string {
	return text
		.toLowerCase()
		.replace(/[''ʻʼ`]/g, "") // Uzbek Latin diacritics
		.replace(/[-_]/g, " ")
		.trim();
}

// Replace А/О and a/o with a neutral placeholder for phonetic comparison
function normalizeAO(text: string): string {
	return text.replace(/[аоАО]/g, "\x00").replace(/[aoAO]/g, "\x00");
}

/**
 * Returns true if `haystack` matches the `query` under any of:
 *  - direct substring
 *  - A/O–normalised substring
 *  - Latin→Cyrillic transliteration (+ A/O normalisation on top)
 */
export function matchesQuery(haystack: string, query: string): boolean {
	if (!query.trim()) return true;
	const q = normalizeBase(query);
	const h = normalizeBase(haystack);

	if (h.includes(q)) return true;
	if (normalizeAO(h).includes(normalizeAO(q))) return true;

	if (/[a-z]/.test(q)) {
		const qCyrl = transliterateLatnToCyrl(q);
		if (h.includes(qCyrl)) return true;
		if (normalizeAO(h).includes(normalizeAO(qCyrl))) return true;
	}

	return false;
}
