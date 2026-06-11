/**
 * Mini donut ring showing required-fields completion inside the smart CTA
 * («Ещё N полей» → «Далее/Сохранить»). Drawn white-on-translucent so it
 * reads on the primary button background; the arc animates smoothly as
 * fields get filled.
 */
export function RequiredProgressRing({
	filled,
	total,
	size = 18,
	strokeWidth = 2.5,
}: {
	filled: number;
	total: number;
	size?: number;
	strokeWidth?: number;
}) {
	const r = (size - strokeWidth) / 2;
	const c = 2 * Math.PI * r;
	const frac = total > 0 ? Math.min(Math.max(filled / total, 0), 1) : 0;
	return (
		<svg
			width={size}
			height={size}
			viewBox={`0 0 ${size} ${size}`}
			style={{ flexShrink: 0 }}
			aria-hidden="true"
		>
			<circle
				cx={size / 2}
				cy={size / 2}
				r={r}
				fill="none"
				stroke="rgba(255,255,255,0.35)"
				strokeWidth={strokeWidth}
			/>
			<circle
				cx={size / 2}
				cy={size / 2}
				r={r}
				fill="none"
				stroke="#fff"
				strokeWidth={strokeWidth}
				strokeLinecap="round"
				strokeDasharray={c}
				strokeDashoffset={c * (1 - frac)}
				transform={`rotate(-90 ${size / 2} ${size / 2})`}
				style={{ transition: "stroke-dashoffset 300ms ease" }}
			/>
		</svg>
	);
}
