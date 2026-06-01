// Aura line icons — Lucide-style 24×24 strokes. Size via CSS width/height.
import type { SVGProps } from 'react';

type Seg = string | { t: 'rect' | 'circle'; [k: string]: string | number };

function make(paths: Seg | Seg[], opts: { fill?: string; sw?: number } = {}) {
  const list = Array.isArray(paths) ? paths : [paths];
  const Comp = (props: SVGProps<SVGSVGElement>) => (
    <svg
      viewBox="0 0 24 24"
      fill={opts.fill || 'none'}
      stroke={opts.fill ? 'none' : 'currentColor'}
      strokeWidth={opts.sw ?? 1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      {list.map((d, i) => {
        if (typeof d === 'string') return <path d={d} key={i} />;
        const { t, ...rest } = d;
        if (t === 'rect') return <rect key={i} {...(rest as SVGProps<SVGRectElement>)} />;
        return <circle key={i} {...(rest as SVGProps<SVGCircleElement>)} />;
      })}
    </svg>
  );
  return Comp;
}

export const Icon = {
  Home: make(['M3 10.5 12 3l9 7.5', 'M5 9.5V20a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9.5', 'M9.5 21v-6h5v6']),
  Calendar: make(['M3 8.5h18', { t: 'rect', x: 3, y: 4.5, width: 18, height: 16, rx: 2 }, 'M8 2.5v4', 'M16 2.5v4', 'M7.5 13h2', 'M11 13h2', 'M14.5 13h2', 'M7.5 16.5h2', 'M11 16.5h2']),
  Check: make('M5 12.5l4.2 4.2L19 7'),
  CheckSquare: make(['M9 11.5l2.2 2.2L15.5 9', { t: 'rect', x: 3.5, y: 3.5, width: 17, height: 17, rx: 3 }]),
  Cloud: make('M7 17.5a4 4 0 0 1-.4-7.98 5 5 0 0 1 9.6-1.36A3.75 3.75 0 0 1 17.5 17.5z'),
  CloudSun: make(['M8 16.5a3.5 3.5 0 0 1-.3-6.98', 'M15 9.2a4 4 0 0 1 2.6 7.3', { t: 'circle', cx: 12, cy: 7.5, r: 2.6 }, 'M12 2.5v1.4', 'M6.5 4.8l1 1', 'M17.5 4.8l-1 1', 'M3.5 10.5h1.4']),
  Trending: make(['M3 16.5l5.5-5.5 3.5 3.5L21 6.5', 'M15.5 6.5H21v5.5']),
  Wallet: make([{ t: 'rect', x: 3, y: 6, width: 18, height: 13, rx: 2.5 }, 'M3 10h18', 'M16.5 14.5h.01']),
  Bot: make([{ t: 'rect', x: 4, y: 8, width: 16, height: 12, rx: 3 }, 'M12 8V4.5', { t: 'circle', cx: 12, cy: 3.5, r: 1 }, 'M9 13.5h.01', 'M15 13.5h.01', 'M2 13v3', 'M22 13v3']),
  Send: make('M5 12h13M13 6l6 6-6 6'),
  Sun: make([{ t: 'circle', cx: 12, cy: 12, r: 4 }, 'M12 2v2', 'M12 20v2', 'M4 12H2', 'M22 12h-2', 'M5.6 5.6l1.4 1.4', 'M17 17l1.4 1.4', 'M18.4 5.6L17 7', 'M7 17l-1.4 1.4']),
  Moon: make('M21 12.8A8.5 8.5 0 1 1 11.2 3a6.6 6.6 0 0 0 9.8 9.8z'),
  Sparkle: make('M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z'),
  LogOut: make(['M15 12H4', 'M8 8l-4 4 4 4', 'M11 4h6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-6']),
  Car: make(['M5 13l1.5-4.5A2 2 0 0 1 8.4 7h7.2a2 2 0 0 1 1.9 1.5L19 13', { t: 'rect', x: 3, y: 13, width: 18, height: 5, rx: 1.5 }, 'M7 18v1.5', 'M17 18v1.5', 'M6.5 15.5h.01', 'M17.5 15.5h.01']),
  Train: make([{ t: 'rect', x: 5, y: 4, width: 14, height: 12, rx: 3 }, 'M5 11h14', 'M8.5 19l-1.5 2', 'M15.5 19l1.5 2', 'M9 14h.01', 'M15 14h.01']),
  Mountain: make('M3 19h18L14.5 7l-3.2 5.4-2-2.6z'),
  Music: make(['M9 18V5l11-2v13', { t: 'circle', cx: 6.5, cy: 18, r: 2.5 }, { t: 'circle', cx: 17.5, cy: 16, r: 2.5 }]),
  Map: make(['M9 4.5L3.5 6.7v12.8L9 17.3l6 2.2 5.5-2.2V4.5L15 6.7z', 'M9 4.5v12.8', 'M15 6.7v12.8']),
  Note: make([{ t: 'rect', x: 4, y: 3.5, width: 16, height: 17, rx: 2.5 }, 'M8 8.5h8', 'M8 12h8', 'M8 15.5h5']),
  Target: make([{ t: 'circle', cx: 12, cy: 12, r: 8.5 }, { t: 'circle', cx: 12, cy: 12, r: 4.5 }, { t: 'circle', cx: 12, cy: 12, r: 0.6, fill: 'currentColor' }]),
  Timer: make([{ t: 'circle', cx: 12, cy: 13.5, r: 7.5 }, 'M12 13.5V9.5', 'M9.5 2.5h5']),
  Drop: make('M12 3.5s5.5 5.6 5.5 9.5a5.5 5.5 0 0 1-11 0c0-3.9 5.5-9.5 5.5-9.5z'),
  Wind: make(['M3 9h11a2.5 2.5 0 1 0-2.5-2.5', 'M3 14h15a2.5 2.5 0 1 1-2.5 2.5', 'M3 12h7']),
  Arrow: make('M5 12h14M13 6l6 6-6 6'),
  ArrowUp: make('M12 19V5M6 11l6-6 6 6'),
  ArrowDown: make('M12 5v14M6 13l6 6 6-6'),
  Chevron: make('M9 6l6 6-6 6'),
  ChevronDown: make('M6 9l6 6 6-6'),
  Alert: make(['M12 8.5v4.5', 'M12 16.5h.01', { t: 'circle', cx: 12, cy: 12, r: 8.5 }]),
  Clock: make([{ t: 'circle', cx: 12, cy: 12, r: 8.5 }, 'M12 7.5V12l3 2']),
  Refresh: make(['M3.5 12a8.5 8.5 0 0 1 14.5-6M20.5 12a8.5 8.5 0 0 1-14.5 6', 'M18 3v3.5h-3.5', 'M6 21v-3.5h3.5']),
  Plus: make('M12 5v14M5 12h14'),
  Search: make([{ t: 'circle', cx: 11, cy: 11, r: 7 }, 'M16.5 16.5L21 21']),
  Pin: make(['M12 21s6-5.3 6-10A6 6 0 0 0 6 11c0 4.7 6 10 6 10z', { t: 'circle', cx: 12, cy: 11, r: 2.3 }]),
  Coffee: make(['M4 8h13v5a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5z', 'M17 9h2.5a2.5 2.5 0 0 1 0 5H17', 'M7 3.5v1.5', 'M10.5 3.5v1.5', 'M14 3.5v1.5']),
  Flame: make('M12 3c1 3-2 4-2 7a2 2 0 0 0 4 0c0-1 0-1.5-.3-2.2C16 9.5 17 12 17 14a5 5 0 0 1-10 0c0-3.5 3-5.5 5-11z'),
} as const;

export type IconName = keyof typeof Icon;
