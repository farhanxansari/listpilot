import type { Damage } from "@/lib/api";

// Marker positions on the side-view outline below (car faces right).
const SPOTS: Record<string, [number, number]> = {
  front_bumper: [560, 132],
  rear_bumper: [40, 132],
  bonnet: [505, 104],
  boot: [100, 110],
  roof: [318, 60],
  front_left_door: [372, 126],
  front_right_door: [372, 126],
  rear_left_door: [262, 126],
  rear_right_door: [262, 126],
  left_fender: [505, 126],
  right_fender: [505, 126],
  windshield: [402, 82],
  headlamp: [550, 116],
  taillamp: [45, 116],
  wheel: [462, 150],
  other: [318, 126],
};

/** Side-view car outline with a numbered marker per damage found in the photos. */
export default function InspectionMap({ damages }: { damages: Damage[] }) {
  return (
    <svg
      viewBox="0 0 600 190"
      role="img"
      aria-label={
        damages.length
          ? `Car outline with ${damages.length} damage marker(s)`
          : "Car outline, no damage found"
      }
      className="h-auto w-full"
    >
      <path d="M30 140 Q30 116 62 110 L160 104 Q200 62 262 56 L380 56 Q428 60 468 100 L540 110 Q570 115 570 140 L570 150 L30 150 Z" fill="#F1F4F7" stroke="#0E1B2C" strokeWidth="3" strokeLinejoin="round" />
      <path d="M206 102 L262 64 L372 64 L430 102 Z" fill="#DCE3EA" stroke="#0E1B2C" strokeWidth="2.5" strokeLinejoin="round" />
      <path d="M318 64 L318 102" stroke="#0E1B2C" strokeWidth="2.5" />
      {[160, 462].map((cx) => (
        <g key={cx}>
          <circle cx={cx} cy="150" r="28" fill="#fff" stroke="#0E1B2C" strokeWidth="3" />
          <circle cx={cx} cy="150" r="10" fill="#0E1B2C" />
        </g>
      ))}
      {damages.map((d, i) => {
        const [x, y] = SPOTS[d.location] ?? SPOTS.other;
        const lx = Math.min(Math.max(x + 40, 30), 570);
        const ly = Math.max(y - 50, 18);
        return (
          <g key={i}>
            <circle cx={x} cy={y} r="7" fill="#B91C1C" />
            <path d={`M${x} ${y} L${lx} ${ly}`} stroke="#B91C1C" strokeWidth="2" />
            <circle cx={lx} cy={ly} r="15" fill="#B91C1C" />
            <text x={lx} y={ly + 6} textAnchor="middle" fontSize="16" fontWeight="800" fill="#fff">
              {i + 1}
            </text>
          </g>
        );
      })}
    </svg>
  );
}