import re, sys, json, random, zlib
from collections import defaultdict, Counter

LOC_RE = re.compile(r"^<([^>]+)>")
TAG_RE = re.compile(r"<[^>]+>")
SEC_RE = re.compile(r"\$I=([A-Z])")
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

def sample_counter(cnt: Counter, rng: random.Random, forbid=None):
    items = [(k, v) for k, v in cnt.items() if k != forbid]
    if not items:
        items = list(cnt.items())
    tot = sum(v for _, v in items)
    r = rng.uniform(0, tot)
    upto = 0
    for k, v in items:
        upto += v
        if upto >= r:
            return k
    return items[-1][0]

class VoynichStateMachineCompiler:
    """
    A memoryless 3-stage Line-Envelope + First-Order Markov Word Compiler:
      1. Pos (START / MID / END) + prev_Prefix -> Prefix
      2. Prefix -> Core
      3. (Core, Pos) -> Suffix  (Notice: Suffix is conditionally independent of Prefix!)
    """
    def __init__(self):
        self.p_start = Counter()
        self.p_trans = defaultdict(Counter)  # (pos_bucket, prev_p) -> Counter(p)
        self.p_to_c = defaultdict(Counter)   # p -> Counter(c)
        self.c_pos_to_s = defaultdict(Counter) # (c, pos_bucket) -> Counter(s)
        self.c_to_s_fallback = defaultdict(Counter)

    def train(self, lines):
        for ln in lines:
            prev_p = None
            for i, w in enumerate(ln):
                pos = "START" if i == 0 else ("END" if i == len(ln) - 1 else "MID")
                p, c, s = decompose(w)
                if pos == "START":
                    self.p_start[p] += 1
                else:
                    self.p_trans[(pos, prev_p)][p] += 1
                self.p_to_c[p][c] += 1
                self.c_pos_to_s[(c, pos)][s] += 1
                self.c_to_s_fallback[c][s] += 1
                prev_p = p

    def compile_line(self, length: int, rng: random.Random):
        out = []
        prev_p, prev_w = None, None
        for i in range(length):
            pos = "START" if i == 0 else ("END" if i == length - 1 else "MID")
            for _ in range(5):  # Anti-exact-repeat loop
                if pos == "START":
                    p = sample_counter(self.p_start, rng)
                else:
                    dist = self.p_trans.get((pos, prev_p)) or self.p_start
                    p = sample_counter(dist, rng)
                c = sample_counter(self.p_to_c[p], rng)
                s_dist = self.c_pos_to_s.get((c, pos)) or self.c_to_s_fallback[c]
                s = sample_counter(s_dist, rng)
                w = assemble(p, c, s)
                if w != prev_w:
                    break
            out.append(w)
            prev_p, prev_w = p, w
        return out

def zlib_metrics(lines, seed=1337):
    rng = random.Random(seed)
    shuf = [ rng.sample(ln, len(ln)) for ln in lines ]
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

def evaluate_dialect(lines, seed=1337):
    rng = random.Random(seed)
    idx = list(range(len(lines)))
    rng.shuffle(idx)
    split = int(0.8 * len(idx))
    train = [lines[i] for i in idx[:split]]
    test  = [lines[i] for i in idx[split:]]

    compiler = VoynichStateMachineCompiler()
    compiler.train(train)

    compiled_test = [compiler.compile_line(len(ln), rng) for ln in test]

    train_vocab = set(w for ln in train for w in ln)
    real_test_words = [w for ln in test for w in ln]
    comp_test_words = [w for ln in compiled_test for w in ln]

    real_in_train = sum(1 for w in real_test_words if w in train_vocab) / len(real_test_words)
    comp_in_train = sum(1 for w in comp_test_words if w in train_vocab) / len(comp_test_words)

    return {
        "Real_HeldOut_Test_Metrics": zlib_metrics(test, seed),
        "Compiled_Synthetic_Metrics": zlib_metrics(compiled_test, seed),
        "Real_Test_Words_in_Train_Vocab_%": round(real_in_train * 100, 2),
        "Compiled_Words_in_Real_Train_Vocab_%": round(comp_in_train * 100, 2),
        "Sample_Real_Lines": [".".join(ln) for ln in test[:4]],
        "Sample_Compiled_Lines": [".".join(ln) for ln in compiled_test[:4]]
    }

if __name__ == "__main__":
    by_lang = load_clean_lines(sys.argv[1])
    out = {
        "Currier_A_Compiler_Test": evaluate_dialect(by_lang["A"]),
        "Currier_B_Compiler_Test": evaluate_dialect(by_lang["B"])
    }
    print(json.dumps(out, indent=2))