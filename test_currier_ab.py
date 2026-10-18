import re, sys, json, random, zlib
from collections import defaultdict, Counter

LOC_RE = re.compile(r"^<([^>]+)>")
TAG_RE = re.compile(r"<[^>]+>")
SEC_RE = re.compile(r"\$I=([A-Z])")
LANG_RE = re.compile(r"\$L=([A-Z])")

# True Voynich visual prefix clusters and suffix clusters in EVA
PREFIXES = sorted(
    ("qo", "ch", "sh", "cth", "ckh", "cph", "cfh", "yk", "yt", "ok", "ot", "op", "of", "d", "o", "y", "s", "k", "t", "p", "f"),
    key=len, reverse=True
)
SUFFIXES = sorted(
    ("aiin", "aiir", "aiil", "iin", "edy", "ody", "oldy", "aldy", "ordy", "dy", "ey", "oy", "ly", "ry", "sy", "ky", "ty", "ol", "or", "al", "ar", "am", "an", "om", "in", "r", "l", "s", "m", "n", "y"),
    key=len, reverse=True
)

def load_clean_corpus(path: str):
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
                continue  # Strictly Takahashi (;H) only!

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

def decompose_eva_slots(word: str):
    """Decomposes a Voynich word into (Prefix_Slot, Middle_Core, Suffix_Slot) using true EVA ligatures."""
    p_slot = ""
    rest = word
    for p in PREFIXES:
        if rest.startswith(p) and len(rest) > len(p):
            p_slot = p
            rest = rest[len(p):]
            break

    s_slot = ""
    for s in SUFFIXES:
        if rest.endswith(s) and len(rest) >= len(s)
            s_slot = s
            rest = rest[:-len(s)]
            break

    return (p_slot or "_", rest or "_", s_slot or "_")

def analyze_group(lines):
    words = [w for ln in lines for w in ln]
    slots = [decompose_eva_slots(w) for w in words]
    p_counts = Counter(s[0] for s in slots)
    m_counts = Counter(s[1] for s in slots)
    s_counts = Counter(s[2] for s in slots)
    full_slot_counts = Counter(slots)

    # Adjacent word repetition / 1-slot shift rate within lines
    adj_same_prefix = 0
    adj_same_suffix = 0
    adj_pairs = 0
    for ln in lines:
        ln_slots = [decompose_eva_slots(w) for w in ln]
        for i in range(len(ln_slots) - 1):
            adj_pairs += 1
            if ln_slots[i][0] == ln_slots[i+1][0] and ln_slots[i][0] != "_":
                adj_same_prefix += 1
            if ln_slots[i][2] == ln_slots[i+1][2] and ln_slots[i][2] != "_":
                adj_same_suffix += 1

    return {
        "lines": len(lines),
        "total_words": len(words),
        "unique_vocab": len(set(words)),
        "unique_cores_(middle_slot)": len(m_counts),
        "top5_prefixes": p_counts.most_common(5),
        "top5_cores": m_counts.most_common(5),
        "top5_suffixes": s_counts.most_common(5),
        "top10_core_coverage_%": round(sum(c for _, c in m_counts.most_common(10)) / len(words) * 100, 2),
        "adjacent_same_prefix_%": round(adj_same_prefix / max(1, adj_pairs) * 100, 2),
        "adjacent_same_suffix_%": round(adj_same_suffix / max(1, adj_pairs) * 100, 2),
    }

def cross_dialect_test(lines_a, lines_b):
    cores_a = Counter(decompose_eva_slots(w)[1] for ln in lines_a for w in ln)
    cores_b = Counter(decompose_eva_slots(w)[1] for ln in lines_b for w in ln)
    top50_a = set(k for k, _ in cores_a.most_common(50))
    top50_b = set(k for k, _ in cores_b.most_common(50))

    b_words_covered_by_a_cores = sum(c for k, c in cores_b.items() if k in cores_a) / max(1, sum(cores_b.values()))
    a_words_covered_by_b_cores = sum(c for k, c in cores_a.items() if k in cores_b) / max(1, sum(cores_a.values()))

    return {
        "top50_core_overlap_count": len(top50_a & top50_b),
        "B_token_mass_using_A_cores_%": round(b_words_covered_by_a_cores * 100, 2),
        "A_token_mass_using_B_cores_%": round(a_words_covered_by_b_cores * 100, 2),
    }

if __name__ == "__main__":
    by_lang, by_sec = load_clean_corpus(sys.argv[1])
    report = {
        "Currier_A": analyze_group(by_lang.get("A", [])),
        "Currier_B": analyze_group(by_lang.get("B", [])),
        "Cross_Dialect_Core_Transfer": cross_dialect_test(by_lang.get("A", []), by_lang.get("B", [])),
        "By_Section_Summary": {sec: analyze_group(lns) for sec, lns in by_sec.items() if len(lns) >= 100}
    }
    print(json.dumps(report, indent=2))
