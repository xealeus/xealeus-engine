import re, sys, json, math
from collections import defaultdict, Counter

LOC_RE = re.compile(r"^<([^>]+)>")
TAG_RE = re.compile(r"<[^>]+>")
SEC_RE = re.compile(r"\$I=([A-Z])")
LANG_RE = re.compile(r"\$L=([A-Z])")

# Sorted longest-first so 'cth' matches before 'c' or 't', and 'edy' before 'dy' or 'y'
PREFIXES = sorted(
    ("qo", "ch", "sh", "cth", "ckh", "cph", "cfh", "yk", "yt", "ok", "ot", "op", "of", "d", "o", "y", "s", "k", "t", "p", "f"),
    key=len, reverse=True
)
SUFFIXES = sorted(
    ("aiin", "aiir", "aiil", "iin", "edy", "ody", "oldy", "aldy", "ordy", "dy", "ey", "oy", "ly", "ry", "sy", "ky", "ty", "ol", "or", "al", "ar", "am", "an", "om", "in", "r", "l", "s", "m", "n", "y"),
    key=len, reverse=True
)

def load_clean_lines(path: str):
    by_lang = defaultdict(list)
    by_sec = defaultdict(list)
    curr_sec, curr_lang = None, None

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            if "$I=" in raw:
                m_s = SEC_RE.search(raw)
                m_l = LANG_RE.search(raw)
                curr_sec = m_s.group(1) if m_s else curr_sec
                curr_lang = m_l.group(1) if m_l else None
                continue

            m_loc = LOC_RE.match(raw)
            if not m_loc or not m_loc.group(1).endswith(";H"):
                continue

            text = TAG_RE.sub(" ", raw)
            text = re.sub(r"\{[^}]*\}", " ", text)
            text = re.sub(r"[!%?*$]", "", text)
            words = [w for w in re.split(r"[.,\-=\s]+", text) if w and w.isalpha()]
            if words:
                if curr_sec:
                    by_sec[curr_sec].append(words)
                if curr_lang in ("A", "B"):
                    by_lang[curr_lang].append(words)
    return dict(by_lang), dict(by_sec)

def decompose(word: str):
    p_slot = "_"
    rest = word
    for p in PREFIXES:
        if rest.startswith(p) and len(rest) > len(p):
            p_slot = p
            rest = rest[len(p):]
            break
    s_slot = "_"
    for s in SUFFIXES:
        if rest.endswith(s) and len(rest) >= len(s):
            s_slot = s
            rest = rest[:-len(s)]
            break
    return (p_slot, rest or "_", s_slot)

def entropy(counts: Counter):
    total = sum(counts.values())
    if not total: return 0.0
    return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)

def mutual_info(pairs: list):
    total = len(pairs)
    if not total: return {}
    cx = Counter(x for x, _ in pairs)
    cy = Counter(y for _, y in pairs)
    cxy = Counter(pairs)
    hx = entropy(cx)
    hy = entropy(cy)
    hxy = entropy(cxy)
    mi = hx + hy - hxy
    nmi = mi / max(1e-9, min(hx, hy))
    return {"MI_bits": round(mi, 4), "Normalized_MI_%": round(nmi * 100, 2)}

def analyze_line_envelope(lines):
    """Test A: Compare First Word vs Middle Words vs Last Word in lines >= 4 words."""
    pos_p = {"START": Counter(), "MID": Counter(), "END": Counter()}
    pos_s = {"START": Counter(), "MID": Counter(), "END": Counter()}
    for ln in lines:
        if len(ln) < 4:
            continue
        for i, w in enumerate(ln):
            p, c, s = decompose(w)
            bucket = "START" if i == 0 else ("END" if i == len(ln) - 1 else "MID")
            pos_p[bucket][p] += 1
            pos_s[bucket][s] += 1

    def top_pct(cnt, k=5):
        tot = max(1, sum(cnt.values()))
        return [(item, round(c / tot * 100, 1)) for item, c in cnt.most_common(k)]

    return {
        "Prefix_by_LinePos_%": {k: top_pct(v) for k, v in pos_p.items()},
        "Suffix_by_LinePos_%": {k: top_pct(v) for k, v in pos_s.items()}
    }

def analyze_slot_stepping(lines):
    """Test C: When adjacent words share structure, which slot steps/changes?"""
    patterns = Counter()
    total_pairs = 0
    for ln in lines:
        slots = [decompose(w) for w in ln]
        for i in range(len(slots) - 1):
            total_pairs += 1
            p1, c1, s1 = slots[i]
            p2, c2, s2 = slots[i+1]
            same_p = (p1 == p2)
            same_c = (c1 == c2)
            same_s = (s1 == s2)
            if same_p and same_c and same_s:
                patterns["EXACT_REPEAT_(P=P,C=C,S=S)"] += 1
            elif same_p and same_s and not same_c:
                patterns["CORE_STEP_ONLY_(P=P,S=S,C!=C)"] += 1
            elif same_p and same_c and not same_s:
                patterns["SUFFIX_STEP_ONLY_(P=P,C=C,S!=S)"] += 1
            elif same_c and same_s and not same_p:
                patterns["PREFIX_STEP_ONLY_(C=C,S=S,P!=P)"] += 1
            elif same_p:
                patterns["SAME_PREFIX_ONLY"] += 1
            elif same_c:
                patterns["SAME_CORE_ONLY"] += 1
            elif same_s:
                patterns["SAME_SUFFIX_ONLY"] += 1
            else:
                patterns["ALL_3_SLOTS_CHANGE"] += 1

    return {k: round(v / max(1, total_pairs) * 100, 2) for k, v in patterns.most_common()}

def full_deep_analysis(lines):
    all_slots = [decompose(w) for ln in lines for w in ln]
    return {
        "Line_Envelope_(Test_A)": analyze_line_envelope(lines),
        "Slot_Coupling_MI_(Test_B)": {
            "Prefix_vs_Core": mutual_info([(p, c) for p, c, s in all_slots]),
            "Core_vs_Suffix": mutual_info([(c, s) for p, c, s in all_slots]),
            "Prefix_vs_Suffix": mutual_info([(p, s) for p, c, s in all_slots]),
        },
        "Adjacent_Word_Stepping_(Test_C)": analyze_slot_stepping(lines)
    }

if __name__ == "__main__":
    by_lang, by_sec = load_clean_lines(sys.argv[1])
    out = {
        "Currier_A": full_deep_analysis(by_lang.get("A", [])),
        "Currier_B": full_deep_analysis(by_lang.get("B", [])),
        "Sections": {sec: full_deep_analysis(lns) for sec, lns in by_sec.items() if len(lns) >= 200}
    }
    print(json.dumps(out, indent=2))