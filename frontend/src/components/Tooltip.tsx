import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';

const ART: Record<string, string> = {
  connect: `<svg viewBox="0 0 96 64" fill="none"><rect x="8" y="14" width="32" height="36" rx="6" fill="#14b8a6"/><rect x="56" y="18" width="32" height="28" rx="6" fill="#111827"/><path d="M40 32h16" stroke="#14b8a6" stroke-width="3"/><circle cx="40" cy="32" r="3" fill="#14b8a6"/><circle cx="56" cy="32" r="3" fill="#14b8a6"/></svg>`,
  discover: `<svg viewBox="0 0 96 64" fill="none"><circle cx="28" cy="32" r="10" fill="#14b8a6"/><circle cx="68" cy="18" r="8" fill="#111827"/><circle cx="70" cy="48" r="8" fill="#111827"/><path d="M37 28l23-8M36 38l26 8" stroke="#94a3b8" stroke-width="2"/></svg>`,
  profile: `<svg viewBox="0 0 96 64" fill="none"><path d="M18 46a30 30 0 1158 0" stroke="#cbd5e1" stroke-width="8" fill="none"/><path d="M18 46a30 30 0 0146-24" stroke="#14b8a6" stroke-width="8" fill="none"/><circle cx="48" cy="46" r="5" fill="#111827"/></svg>`,
  recommend: `<svg viewBox="0 0 96 64" fill="none"><rect x="16" y="20" width="28" height="28" rx="4" fill="#14b8a6"/><rect x="52" y="14" width="28" height="36" rx="4" fill="#111827"/><path d="M30 30v8M66 24v20" stroke="#fff" stroke-width="3"/></svg>`,
  dryrun: `<svg viewBox="0 0 96 64" fill="none"><path d="M48 10l28 10v16c0 14-12 22-28 26-16-4-28-12-28-26V20z" fill="#ecfdf8" stroke="#14b8a6" stroke-width="3"/><path d="M36 34l8 8 16-16" stroke="#111827" stroke-width="3"/></svg>`,
  migrate: `<svg viewBox="0 0 96 64" fill="none"><rect x="10" y="18" width="28" height="28" rx="5" fill="#94a3b8"/><rect x="58" y="18" width="28" height="28" rx="5" fill="#f59e0b"/><path d="M40 32h16M50 26l8 6-8 6" stroke="#111827" stroke-width="3"/></svg>`,
  validate: `<svg viewBox="0 0 96 64" fill="none"><rect x="22" y="10" width="52" height="44" rx="6" fill="#111827"/><path d="M34 24h28M34 34h20" stroke="#94a3b8" stroke-width="3"/><circle cx="68" cy="44" r="10" fill="#14b8a6"/><path d="M63 44l3 3 7-8" stroke="#fff" stroke-width="2"/></svg>`,
  theme: `<svg viewBox="0 0 96 64" fill="none"><circle cx="36" cy="32" r="14" fill="#fbbf24"/><path d="M58 18a16 16 0 100 28 18 18 0 010-28z" fill="#111827"/></svg>`,
  size: `<svg viewBox="0 0 96 64" fill="none"><rect x="12" y="28" width="16" height="16" rx="3" fill="#94a3b8"/><rect x="36" y="20" width="20" height="24" rx="3" fill="#14b8a6"/><rect x="64" y="12" width="22" height="36" rx="3" fill="#111827"/></svg>`,
  readonly: `<svg viewBox="0 0 96 64" fill="none"><rect x="20" y="22" width="56" height="28" rx="6" fill="#ecfdf8" stroke="#14b8a6" stroke-width="3"/><path d="M32 22v-4a16 16 0 0132 0v4" stroke="#111827" stroke-width="3"/></svg>`,
};

export default function Tooltip({
  title,
  text,
  art = 'connect',
  children,
}: {
  title: string;
  text: string;
  art?: keyof typeof ART;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [style, setStyle] = useState<CSSProperties>({});
  const root = useRef<HTMLSpanElement>(null);

  const place = () => {
    const box = root.current?.getBoundingClientRect();
    if (!box) return;
    const width = 220;
    const inSidebar = Boolean(root.current?.closest('.steps'));
    if (inSidebar) {
      setStyle({
        position: 'fixed',
        left: Math.min(box.right + 10, window.innerWidth - width - 8),
        top: Math.max(8, box.top),
        width,
      });
      return;
    }
    const left = Math.min(Math.max(8, box.left), window.innerWidth - width - 8);
    const showAbove = box.bottom + 96 > window.innerHeight;
    setStyle({
      position: 'fixed',
      left,
      width,
      top: showAbove ? undefined : box.bottom + 8,
      bottom: showAbove ? window.innerHeight - box.top + 8 : undefined,
    });
  };

  useEffect(() => {
    if (!open) return;
    place();
    const hide = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener('scroll', place, true);
    window.addEventListener('resize', place);
    document.addEventListener('mousedown', hide);
    return () => {
      window.removeEventListener('scroll', place, true);
      window.removeEventListener('resize', place);
      document.removeEventListener('mousedown', hide);
    };
  }, [open]);

  return (
    <span
      ref={root}
      className={`tip${open ? ' open' : ''}`}
      onMouseEnter={() => { place(); setOpen(true); }}
      onMouseLeave={() => setOpen(false)}
      onClick={() => setOpen(false)}
    >
      {children}
      <span className="tip-card" role="tooltip" style={style}>
        <span className="tip-head">
          <span className="tip-art" dangerouslySetInnerHTML={{ __html: ART[art] || ART.connect }} />
          <strong>{title}</strong>
        </span>
        <em>{text}</em>
      </span>
    </span>
  );
}
