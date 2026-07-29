def fallback_palette(theme: str) -> dict[str, str]:
    if any(key in theme for key in ["科技", "赛博"]):
        return {"bg": "radial-gradient(circle at 25% 20%,#12364f 0,#0b1220 45%,#050816 100%)", "texture": "linear-gradient(120deg,rgba(34,211,238,.15),transparent 35%,rgba(99,102,241,.12))", "text": "#e5f7ff", "muted": "#9fb6c5", "accent": "#22d3ee", "line": "rgba(34,211,238,.28)", "panel": "rgba(8,20,36,.66)", "card": "rgba(15,34,58,.74)", "radius": "6px"}
    if "终端" in theme:
        return {"bg": "linear-gradient(135deg,#0a0f0a,#101810)", "texture": "linear-gradient(rgba(74,222,128,.08) 1px,transparent 1px)", "text": "#dcfce7", "muted": "#86efac", "accent": "#22c55e", "line": "rgba(34,197,94,.32)", "panel": "rgba(6,20,12,.72)", "card": "rgba(8,32,18,.78)", "radius": "4px"}
    if any(key in theme for key in ["中国", "中式", "宣纸", "竹简"]):
        return {"bg": "linear-gradient(135deg,#fbf7ef,#efe3cf)", "texture": "radial-gradient(circle at 82% 16%,rgba(127,29,29,.12),transparent 28%)", "text": "#3f2416", "muted": "#7c5c45", "accent": "#9f1239", "line": "rgba(127,29,29,.20)", "panel": "rgba(255,251,235,.72)", "card": "rgba(255,247,237,.84)", "radius": "2px"}
    if any(key in theme for key in ["商务", "答辩", "星月蓝"]):
        return {"bg": "linear-gradient(135deg,#f8fafc,#dbeafe)", "texture": "linear-gradient(90deg,rgba(15,23,42,.06),transparent)", "text": "#0f172a", "muted": "#475569", "accent": "#2563eb", "line": "rgba(37,99,235,.28)", "panel": "rgba(255,255,255,.72)", "card": "rgba(255,255,255,.84)", "radius": "6px"}
    if any(key in theme for key in ["森林", "清新"]):
        return {"bg": "linear-gradient(135deg,#f7fee7,#dcfce7)", "texture": "radial-gradient(circle at 85% 18%,rgba(34,197,94,.16),transparent 28%)", "text": "#16351f", "muted": "#4b7057", "accent": "#16a34a", "line": "rgba(22,163,74,.24)", "panel": "rgba(255,255,255,.68)", "card": "rgba(240,253,244,.9)", "radius": "8px"}
    if any(key in theme for key in ["日落", "速度", "大气红"]):
        return {"bg": "linear-gradient(135deg,#fff7ed,#fee2e2)", "texture": "radial-gradient(circle at 82% 20%,rgba(239,68,68,.18),transparent 30%)", "text": "#431407", "muted": "#9a3412", "accent": "#dc2626", "line": "rgba(220,38,38,.24)", "panel": "rgba(255,247,237,.75)", "card": "rgba(255,237,213,.86)", "radius": "6px"}
    if any(key in theme for key in ["星月夜", "五彩斑斓的黑"]):
        return {"bg": "linear-gradient(135deg,#09090b,#1e1b4b)", "texture": "radial-gradient(circle at 80% 18%,rgba(250,204,21,.18),transparent 24%)", "text": "#fafafa", "muted": "#cbd5e1", "accent": "#facc15", "line": "rgba(250,204,21,.24)", "panel": "rgba(24,24,27,.68)", "card": "rgba(39,39,42,.82)", "radius": "6px"}
    return {"bg": "linear-gradient(135deg,#ffffff 0%,#f7f8fb 52%,#eef2f7 100%)", "texture": "linear-gradient(120deg,rgba(15,23,42,.035),transparent 42%),radial-gradient(circle at 86% 18%,rgba(148,163,184,.16),transparent 30%)", "text": "#111827", "muted": "#64748b", "accent": "#334155", "line": "rgba(15,23,42,.14)", "panel": "rgba(255,255,255,.78)", "card": "rgba(248,250,252,.9)", "radius": "6px"}
