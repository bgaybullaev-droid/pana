export function formatPhone(raw: string | undefined | null): string {
	if (!raw) return "";
	
	// Default to original if it's some other country code and has more numbers (unlikely, but safe)
	const allDigits = raw.replace(/\D/g, "");
	if (allDigits.length > 0 && !allDigits.startsWith("998") && allDigits.length !== 9) {
		return raw;
	}

	const digits = allDigits.replace(/^998/, "").slice(0, 9);
	if (!digits) return raw;

	const parts: string[] = [];
	if (digits.length > 0) parts.push(digits.slice(0, 2));
	if (digits.length > 2) parts.push(digits.slice(2, 5));
	if (digits.length > 5) parts.push(digits.slice(5, 7));
	if (digits.length > 7) parts.push(digits.slice(7, 9));

	return `+998 ${parts.join(" ")}`;
}
