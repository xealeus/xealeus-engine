import re, sys, json, math
from collections import defaultdict, Counter

LOC_RE = re.compile(r"^<([^>]+)>")
TAG_RE = re.compile(r"<[^>]+>")

PREFIXES = sorted(
    ("qo", "ch", "sh", "cth", "ckh", "cph", "cfh", "yk", "yt", "ok", "ot", "op", "of", "d", "o", "y", "s", "k", "t", "p", "f"),
    key=len, reverse=True
)
SUFFIXES = sorted(
    ("aiin", "aiir", "aiil", "iin", "edy", "ody", "oldy", "aldy", "ordy", "dy", "ey", "oy", "ly", "ry", "sy", "ky", "ty", "ol", "or", "al", "ar", "am", "an", "om", "in", "r", "l", "s", "m", "n", "y"),
    key=len, reverse=True
)

def classify_locator(loc: str):
    """
    Classifies IVTFF locator <fNNN.unit;H> into physical geometry on the page:
      - PARAGRAPH: standard horizontal text blocks (.P, @P, +P, *P)
      - RING: circular text rings around hubs (.C, .R, @C, @R)
      - SPOKE: radial lines along spokes/rays (.S, @S)
      - LABEL: discrete component labels (.L, @L)
    """
    # Check @/+/* style tags (e.g. <f1r.1,@P0;H> or <f67r1.1,@Cr;H>)
    if "," in loc:
        code = loc.split(",")[1].split(";")[0]
        if "P" in code: return "PARAGRAPH"
        if "C" in code or "R" in code: return "RING"
        if "S" in code: return "SPOKE"
        if "L" in code: return "LABEL"
    # Check dot-unit tags (e.g. <f70v2.S1.1;H> or <f68v2.C.1;H>)
    parts = loc.split(";")[0].split(".")
    if len(parts) >= 2:
        u = parts[1].upper()
        if u.startswith("P"): return "PARAGRAPH"
        if u.startswith("C") or u.startswith("R"): return "RING"
        if u.startswith("S"): return "SPOKE"
        if u.startswith("L"): return "LABEL"
    return "OTHER"

def load_by_geometry(path: str):
    geom_lines = defaultdict(list)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            m_loc = LOC_RE.match(raw)
            if not m_loc or not m_loc.group(1).endswith(";H"):
                continue
            loc = m_loc.group(1)
            gtype = classify_locator(loc)

            text = TAG_RE.sub(" ", raw)
            text = re.sub(r"\{[^}]*\}", " ", text)
            text = re.sub(r"[!%?*$]", "", text)
            words = [w for w in re.split(r"[.,\-=\s]+", text) if w and w.isalpha()]
            if words:
                geom_lines[gtype].append((loc, words))
    return dict(geom_lines)

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

def edit_distance_1_or_2(w1: str, w2: str):
    """Checks if two words differ by at most 2 character edits (Timm stepping)."""
    if w1 == w2: return False
    if abs(len(w1) - len(w2)) > 2: return False
    # Simple Levenshtein bounded check
    dp = list(range(len(w2) + 1))
    for i, c1 in enumerate(w1):
        new_dp = [i + 1]
        for j, c2 in enumerate(w2):
            cost = 0 if c1 == c2 else 1
            new_dp.append(min(new_dp[-1] + 1, dp[j + 1] + 1, dp[j] + cost))
        dp = new_dp
    return 1 <= dp[-1] <= 2

def analyze_geometry(entries):
    lines = [w for _, w in entries]
    words = [w for ln in lines for w in ln]
    slots = [decompose(w) for w in words]

    p_cnt = Counter(s[0] for s in slots)
    c_cnt = Counter(s[1] for s in slots)
    s_cnt = Counter(s[2] for s in slots)

    # Check internal reduplication / loop tokens (like oteotey, okeoky, kolol)
    loop_tokens = []
    for w in words:
        for sub_len in (2, 3):
            if len(w) >= sub_len * 2:
                for k in range(len(w) - sub_len * 2 + 1):
                    chunk = w[k:k+sub_len]
                    if chunk in ("ii", "ee", "oo"): continue
                    if w[k+sub_len:k+sub_len*2] == chunk:
                        loop_tokens.append(w)
                        break

    # Sequential stepping (horizontal along line, or line-to-line for 1-word labels/spokes)
    seq_words = words if sum(len(ln) for ln in lines) / max(1, len(lines)) < 2.5 else None
    adj_pairs = []
    if seq_words:
        adj_pairs = list(zip(seq_words[:-1], seq_words[1:]))
    else:
        for ln in lines:
            adj_pairs.extend(zip(ln[:-1], ln[1:]))

    near_clone_steps = sum(1 for w1, w2 in adj_pairs if edit_distance_1_or_2(w1, w2))
    same_prefix_steps = sum(1 for w1, w2 in adj_pairs if decompose(w1)[0] == decompose(w2)[0] and decompose(w1)[0] != "_")

    # Ring wrap-around check: how often does END word of a line share Prefix/Core with START word of same line?
    wrap_match = 0
    long_lines = [ln for ln in lines if len(ln) >= 5]
    for ln in long_lines:
        s_start = decompose(ln[0])
        s_end = decompose(ln[-1])
        if (s_start[0] == s_end[0] and s_start[0] != "_") or (s_start[1] == s_end[1] and s_start[1] != "_"):
            wrap_match += 1

    return {
        "line_count": len(lines),
        "total_words": len(words),
        "avg_words_per_line": round(len(words) / max(1, len(lines)), 2),
        "top5_prefixes": p_cnt.most_common(5),
        "top5_cores": c_cnt.most_common(5),
        "top5_suffixes": s_cnt.most_common(5),
        "adjacent_1_or_2_char_mutation_%": round(near_clone_steps / max(1, len(adj_pairs)) * 100, 2),
        "adjacent_same_prefix_%": round(same_prefix_steps / max(1, len(adj_pairs)) * 100, 2),
        "start_end_wrap_coupling_%": round(wrap_match / max(1, len(long_lines)) * 100, 2),
        "internal_loop_reduplication_%": round(len(loop_tokens) / max(1, len(words)) * 100, 2),
        "sample_loop_words": list(dict.fromkeys(loop_tokens))[:12]
    }

def vertical_column_coupling(entries):
    """Measures vertical coupling (Word[L, col] vs Word[L+1, col] and Word[L+1, col+1] diagonal shift)."""
    lines = [w for _, w in entries if len(w) >= 5]
    vert_pairs = 0
    exact_or_near_vert = 0
    diag_right_shift = 0
    same_core_vert = 0

    for idx in range(len(lines) - 1):
        l1, l2 = lines[idx], lines[idx + 1]
        min_len = min(len(l1), len(l2))
        for col in range(min_len):
            vert_pairs += 1
            w_up = l1[col]
            w_dn = l2[col]
            if w_up == w_dn or edit_distance_1_or_2(w_up, w_dn):
                exact_or_near_vert += 1
            if decompose(w_up)[1] == decompose(w_dn)[1]:
                same_core_vert += 1
            if col + 1 < len(l2):
                w_diag = l2[col + 1]
                if w_up == w_diag or edit_distance_1_or_2(w_up, w_diag):
                    diag_right_shift += 1

    # Random non-adjacent line baseline
    baseline_near = 0
    base_pairs = 0
    for idx in range(len(lines) - 10):
        l1, l2 = lines[idx], lines[idx + 10]
        for col in range(min(len(l1), len(l2))):
            base_pairs += 1
            if l1[col] == l2[col] or edit_distance_1_or_2(l1[col], l2[col]):
                baseline_near += 1

    return {
        "vertical_adjacent_line_mutation_match_%": round(exact_or_near_vert / max(1, vert_pairs) * 100, 2),
        "diagonal_right_shift_mutation_match_%": round(diag_right_shift / max(1, vert_pairs) * 100, 2),
        "vertical_distant_line_baseline_%": round(baseline_near / max(1, base_pairs) * 100, 2),
        "vertical_same_core_%": round(same_core_vert / max(1, vert_pairs) * 100, 2)
    }

if __name__ == "__main__":
    geom = load_by_geometry(sys.argv[1])
    out = {
        "By_Diagram_Geometry": {k: analyze_geometry(v) for k, v in geom.items() if len(v) >= 20},
        "Vertical_2D_Grid_Coupling_(Paragraphs)": vertical_column_coupling(geom.get("PARAGRAPH", []))
    }
    print(json.dumps(out, indent=2))
