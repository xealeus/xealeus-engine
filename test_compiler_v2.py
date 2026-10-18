import re, sys, json, math, random, zlib
from collections import defaultdict, Counter

LOC_RE = re.compile(r"^<([^>]+)>")
TAG_RE = re.compile(r"<[^>]+>")
LANG_RE = re.compile(r"\$L=([A-Z])")

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
    curr_lang = None
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            if "$I=" in raw:
                m_l = LANG_RE.search(raw)
                curr_lang = m_l.group(1) if m_l else None
                continue
            m_loc = LOC_RE.match(raw)
            if not m_loc or not m_loc.group(1).endswith(";H"):
                continue
            text = TAG_RE.sub(" ", raw)
            text = re.sub(r"\{[^}]*\}", " ", text)
            text = re.sub(r"[!%?*$]", "", text)
            words = [w for w in re.split(r"[.,\-=\s]+", text) if w and w.isalpha()]
            if len(words) >= 3 and curr_lang in ("A", "B"):
                by_lang[curr_lang].append(words)
    return dict(by_lang)

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

def assemble(p, c, s):
    return ("" if p == "_" else p) + ("" if c == "_" else c) + ("" if s == "_" else s)

def entropy(counts: Counter):
    tot = sum(counts.values())
    if not tot: return 0.0
    return -sum((c / tot) * math.log2(c / tot) for c in counts.values() if c > 0)

def mi_bits(pairs):
    if not pairs: return 0.0
    cx = Counter(x for x, _ in pairs)
    cy = Counter(y for _, y in pairs)
    cxy = Counter(pairs)
    return round(entropy(cx) + entropy(cy) - entropy(cxy), 4)

def cross_word_matrix(lines):
    """Measures all 9 slot-to-slot couplings from Word[t] -> Word[t+1]."""
    adj = []
    for ln in lines:
        slots = [decompose(w) for w in ln]
        for i in range(len(slots) - 1):
            adj.append((slots[i], slots[i+1]))

    names = ("Prefix", "Core", "Suffix")
    matrix = {}
    for i, n1 in enumerate(names):
        for j, n2 in enumerate(names):
            pairs = [(s1[i], s2[j]) for s1, s2 in adj]
            matrix[f"{n1}[t]_to_{n2}[t+1]_MI_bits"] = mi_bits(pairs)
    return matrix

def sample_counter(cnt: Counter, rng: random.Random):
    if not cnt:
        return "_"
    items = list(cnt.items())
    tot = sum(v for _, v in items)
    r = rng.uniform(0, tot)
    upto = 0
    for k, v in items:
        upto += v
        if upto >= r:
            return k
    return items[-1][0]

class VoynichCompilerV2:
    """
    Compiler v2: Adds Inter-Word Domino Chaining & Core/Suffix Memory
      - Prefix[t] depends on (pos, prev_Prefix, prev_Suffix)
      - Core[t]   depends on (Prefix[t], prev_Core) with backoff to (Prefix[t])
      - Suffix[t] depends on (Core[t], pos, prev_Suffix) with backoff to (Core[t], pos)
    """
    def __init__(self):
        self.p_start = Counter()
        self.p_domino = defaultdict(Counter)
        self.p_prev = defaultdict(Counter)
        self.c_start = defaultdict(Counter)
        self.c_mem = defaultdict(Counter)
        self.s_mem = defaultdict(Counter)
        self.s_fallback = defaultdict(Counter)
        self.s_global = defaultdict(Counter)

    def train(self, lines):
        for ln in lines:
            prev_p, prev_c, prev_s = None, None, None
            for i, w in enumerate(ln):
                pos = "START" if i == 0 else ("END" if i == len(ln) - 1 else "MID")
                p, c, s = decompose(w)
                self.s_global[c][s] += 1
                if pos == "START":
                    self.p_start[p] += 1
                    self.c_start[p][c] += 1
                    self.s_fallback[(c, pos)][s] += 1
                else:
                    self.p_domino[(pos, prev_p, prev_s)][p] += 1
                    self.p_prev[(pos, prev_p)][p] += 1
                    self.c_mem[(p, prev_c)][c] += 1
                    self.c_start[p][c] += 1
                    self.s_mem[(c, pos, prev_s)][s] += 1
                    self.s_fallback[(c, pos)][s] += 1
                prev_p, prev_c, prev_s = p, c, s

    def compile_line(self, length: int, rng: random.Random):
        out = []
        prev_p, prev_c, prev_s, prev_w = None, None, None, None
        for i in range(length):
            pos = "START" if i == 0 else ("END" if i == length - 1 else "MID")
            for _ in range(6):
                if pos == "START":
                    p = sample_counter(self.p_start, rng)
                    c = sample_counter(self.c_start[p], rng)
                    s_dist = self.s_fallback.get((c, pos)) or self.s_global[c]
                    s = sample_counter(s_dist, rng)
                else:
                    p_dist = self.p_domino.get((pos, prev_p, prev_s)) or self.p_prev.get((pos, prev_p)) or self.p_start
                    p = sample_counter(p_dist, rng)
                    c_dist = self.c_mem.get((p, prev_c)) or self.c_start[p]
                    c = sample_counter(c_dist, rng)
                    s_dist = self.s_mem.get((c, pos, prev_s)) or self.s_fallback.get((c, pos)) or self.s_global[c]
                    s = sample_counter(s_dist, rng)
                w = assemble(p, c, s)
                if w != prev_w:
                    break
            out.append(w)
            prev_p, prev_c, prev_s, prev_w = p, c, s, w
        return out

def zlib_metrics(lines, seed=1337):
    rng = random.Random(seed)
    shuf = [rng.sample(ln, len(ln)) for ln in lines]
    raw_bytes = "\n".join(".".join(ln) for ln in lines).encode("utf-8")
    shuf_bytes = "\n".join(".".join(ln) for ln in shuf).encode("utf-8")
    n_words = max(1, sum(len(ln) for ln in lines))
    b_orig = len(zlib.compress(raw_bytes, 9)) * 8.0 / n_words
    b_shuf = len(zlib.compress(shuf_bytes, 9)) * 8.0 / n_words
    return {
        "zlib_bits_per_word": round(b_orig, 3),
        "zlib_shuffled_bits_per_word": round(b_shuf, 3),
        "order_delta_bits": round(b_shuf - b_orig, 3)
    }

def evaluate_v2(lines, seed=1337):
    rng = random.Random(seed)
    idx = list(range(len(lines)))
    rng.shuffle(idx)
    split = int(0.8 * len(idx))
    train = [lines[i] for i in idx[:split]]
    test  = [lines[i] for i in idx[split:]]

    compiler = VoynichCompilerV2()
    compiler.train(train)
    compiled_test = [compiler.compile_line(len(ln), rng) for ln in test]

    train_vocab = set(w for ln in train for w in ln)
    comp_words = [w for ln in compiled_test for w in ln]
    comp_in_train = sum(1 for w in comp_words if w in train_vocab) / len(comp_words)

    return {
        "Cross_Word_Slot_Coupling_MI_bits": cross_word_matrix(train),
        "Real_HeldOut_Test_Metrics": zlib_metrics(test, seed),
        "Compiler_V2_Synthetic_Metrics": zlib_metrics(compiled_test, seed),
        "Compiler_V2_Words_in_Train_Vocab_%": round(comp_in_train * 100, 2),
        "Sample_V2_Compiled_Lines": [".".join(ln) for ln in compiled_test[:4]]
    }

if __name__ == "__main__":
    by_lang = load_clean_lines(sys.argv[1])
    out = {
        "Currier_A": evaluate_v2(by_lang["A"]),
        "Currier_B": evaluate_v2(by_lang["B"])
    }
    print(json.dumps(out, indent=2))