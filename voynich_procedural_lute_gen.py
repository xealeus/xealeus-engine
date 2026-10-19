#!/usr/bin/env python3
"""
voynich_procedural_lute_gen.py — Procedural Voynich State-Machine Lute Duet Generator
=====================================================================================
Trains VoynichCompilerV2 on Currier A (Discant Lute) and Currier B (Tenor Lute),
then procedurally generates a brand-new, randomized "faux Voynich" manuscript score
and synthesizes it into a 15th-century Karplus-Strong Lute Duo in Tempus Perfectum (3/4).

Usage:
    python3 voynich_procedural_lute_gen.py [LSI_ivtff_0d.txt] [num_lines] [optional_seed]
"""

import sys
import os
import re
import math
import time
import random
import wave
import struct
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

# 15th-Century D-Dorian Modal Tuning (D, E, F, G, A, B, C)
DISCANT_SCALE = [293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]  # Octave 4 (Currier A)
TENOR_SCALE   = [146.83, 164.81, 174.61, 196.00, 220.00, 246.94, 261.63]  # Octave 3 (Currier B)

# Tempus Perfectum (3-Beat Medieval Tactus)
BEAT = 0.28
MEASURE = BEAT * 3.0  # 0.84s per 3-beat bar

CORE_TO_DEGREE = {
    "_":  0,  # D (Finalis / Root)
    "e":  1,  # E (2nd)
    "ch": 2,  # F (Minor 3rd)
    "k":  3,  # G (4th)
    "a":  4,  # A (5th / Tenor Reciting Tone)
    "o":  5,  # B (Dorian 6th)
    "t":  6,  # C (Subtonic 7th)
}

LUTE_CACHE = {}

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

def core_to_degree(core: str) -> int:
    if core in CORE_TO_DEGREE:
        return CORE_TO_DEGREE[core]
    return sum(ord(c) for c in core) % 7

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
    Procedural State-Machine Compiler V2:
      - Prefix[t] conditioned on (LinePos, prev_Prefix, prev_Suffix)
      - Core[t]   conditioned on (Prefix[t], prev_Core) [1.20 bits MI Domino Link]
      - Suffix[t] conditioned on (Core[t], LinePos, prev_Suffix)
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

    def compile_step(self, pos: str, prev_state, rng: random.Random, harmonic_core_hint=None):
        """
        Generates a single (w, p, c, s) step.
        If `harmonic_core_hint` is passed (modeling the 16.03% 2D vertical core persistence),
        the compiler can lock its Middle Core to the partner lute while keeping its own dialect suffix!
        """
        prev_p, prev_c, prev_s, prev_w = prev_state
        for _ in range(6):
            if pos == "START":
                p = sample_counter(self.p_start, rng)
                c = harmonic_core_hint if (harmonic_core_hint and rng.random() < 0.25) else sample_counter(self.c_start[p], rng)
                s_dist = self.s_fallback.get((c, pos)) or self.s_global[c] or self.s_fallback.get(("_", pos))
                s = sample_counter(s_dist, rng)
            else:
                p_dist = self.p_domino.get((pos, prev_p, prev_s)) or self.p_prev.get((pos, prev_p)) or self.p_start
                p = sample_counter(p_dist, rng)
                if harmonic_core_hint and rng.random() < 0.20:
                    c = harmonic_core_hint
                else:
                    c_dist = self.c_mem.get((p, prev_c)) or self.c_start[p]
                    c = sample_counter(c_dist, rng)
                s_dist = self.s_mem.get((c, pos, prev_s)) or self.s_fallback.get((c, pos)) or self.s_global[c] or self.s_fallback.get(("_", pos))
                s = sample_counter(s_dist, rng)

            w = assemble(p, c, s)
            if not w:
                w = "daiin" if pos != "END" else "am"
                p, c, s = decompose(w)
            if w != prev_w:
                break
        return w, (p, c, s, w)

def generate_procedural_duet_score(comp_a: VoynichCompilerV2, comp_b: VoynichCompilerV2, num_lines: int, rng: random.Random):
    """
    Procedurally compiles `num_lines` of paired Currier A (Discant) and Currier B (Tenor) lines,
    coupling their cores vertically at ~20% to mirror the manuscript's 16.03% 2D column persistence.
    """
    lines_a, lines_b = [], []
    for _ in range(num_lines):
        # Typical Voynich paragraph line length: 7 to 10 words
        line_len = rng.randint(7, 10)
        ln_a, ln_b = [], []
        state_a = (None, None, None, None)
        state_b = (None, None, None, None)

        for i in range(line_len):
            pos = "START" if i == 0 else ("END" if i == line_len - 1 else "MID")
            w_a, state_a = comp_a.compile_step(pos, state_a, rng)
            core_a = state_a[1]
            # Tenor Lute (Currier B) compiles its step with a 2D harmonic hint from Discant's Core
            w_b, state_b = comp_b.compile_step(pos, state_b, rng, harmonic_core_hint=core_a)
            ln_a.append(w_a)
            ln_b.append(w_b)

        lines_a.append(ln_a)
        lines_b.append(ln_b)
    return lines_a, lines_b

def pluck_single_gut_string(freq: float, duration: float, brightness: float = 0.44, damping: float = 0.9945, sr: int = 44100, seed: int = 42):
    n_samples = int(sr * duration)
    delay_len = max(2, int(round(sr / freq)))
    rng = random.Random(seed + int(freq * 100))

    ring = []
    prev = 0.0
    for i in range(delay_len):
        phase = i / delay_len
        noise = rng.uniform(-1.0, 1.0)
        smoothed = (1.0 - brightness) * prev + brightness * noise
        prev = smoothed
        pluck_shape = math.sin(math.pi * phase) * 0.55 + smoothed * 0.45
        ring.append(pluck_shape)

    out = [0.0] * n_samples
    idx = 0
    for i in range(n_samples):
        curr = ring[idx]
        nxt = ring[(idx + 1) % delay_len]
        ring[idx] = damping * (0.52 * curr + 0.48 * nxt)
        out[i] = curr
        idx = (idx + 1) % delay_len

    for i in range(n_samples):
        t = i / sr
        body_env = math.exp(-2.1 * t) * (1.0 - math.exp(-80.0 * t))
        body = 0.18 * math.sin(2.0 * math.pi * freq * t) * body_env
        tail_fade = min(1.0, (n_samples - i) / (0.08 * sr))
        out[i] = (out[i] * 0.85 + body) * tail_fade

    return out

def synth_lute_course(freq: float, ring_dur: float = 2.1, vol: float = 0.28, octave_course: bool = False, sr: int = 44100):
    key = (round(freq, 2), round(ring_dur, 2), round(vol, 3), octave_course)
    if key in LUTE_CACHE:
        return LUTE_CACHE[key]

    s1 = pluck_single_gut_string(freq, ring_dur, brightness=0.42, damping=0.9948, sr=sr, seed=101)
    f2 = (freq * 2.001) if octave_course else (freq * 1.0018)
    s2 = pluck_single_gut_string(f2, ring_dur, brightness=0.38, damping=0.9938, sr=sr, seed=202)

    offset = int(0.0045 * sr)
    n_samples = len(s1)
    combined = [0.0] * n_samples
    for i in range(n_samples):
        val = s1[i] * 0.62
        if i >= offset:
            val += s2[i - offset] * (0.28 if octave_course else 0.48)
        combined[i] = val * vol

    LUTE_CACHE[key] = combined
    return combined

def mix_note(left_buf, right_buf, start_time, note_samples, pan=0.5, sr=44100):
    start_idx = int(start_time * sr)
    needed = start_idx + len(note_samples)
    if needed > len(left_buf):
        ext = needed - len(left_buf)
        left_buf.extend([0.0] * ext)
        right_buf.extend([0.0] * ext)

    l_gain = math.cos(pan * math.pi * 0.5)
    r_gain = math.sin(pan * math.pi * 0.5)
    for i, s in enumerate(note_samples):
        idx = start_idx + i
        left_buf[idx] += s * l_gain
        right_buf[idx] += s * r_gain

def schedule_word_tactus(left_buf, right_buf, t_bar, word, pos, scale, is_discant=True, sr=44100):
    p, c, s = decompose(word)
    deg = core_to_degree(c)
    pan = 0.68 if is_discant else 0.32

    oct_shift = 1.0
    is_gallows = p in ("p", "t", "k", "f", "cth", "ckh", "cph", "cfh")
    if p == "qo":
        oct_shift = 1.5 if not is_discant else 1.0
    elif p == "d" and is_discant:
        oct_shift = 0.5

    base_freq  = scale[deg] * oct_shift
    fifth_freq = scale[(deg + 4) % 7] * oct_shift
    third_freq = scale[(deg + 2) % 7] * oct_shift
    step_freq  = scale[(deg + 1) % 7] * oct_shift

    # 1. Gallows or Line-START Header -> Deep Open-Course Bass Drone on Beat 1
    if is_gallows or pos == "START":
        drone_root = TENOR_SCALE[deg] * 0.5
        mix_note(left_buf, right_buf, t_bar,
                 synth_lute_course(drone_root, ring_dur=2.8, vol=0.30, octave_course=True, sr=sr),
                 pan=0.28)

    # 2. Ring/Zodiac Prefix (ot-, ok-) -> Medieval Plectrum Grace-Note Flick
    t_attack = t_bar
    if p in ("ot", "ok"):
        mix_note(left_buf, right_buf, t_bar,
                 synth_lute_course(third_freq, ring_dur=1.1, vol=0.19, sr=sr),
                 pan=pan)
        t_attack = t_bar + (BEAT * 0.35)

    # 3. Line-End Stop Bit (-am or END) -> 15th-Century "Landini Cadence"
    if s == "am" or pos == "END":
        seventh_f = scale[6]
        sixth_f   = scale[5]
        root_f    = scale[0]
        fifth_f   = scale[4]
        oct_f     = scale[0] * 2.0

        if is_discant:
            mix_note(left_buf, right_buf, t_bar,               synth_lute_course(seventh_f, ring_dur=1.4, vol=0.24, sr=sr), pan=pan)
            mix_note(left_buf, right_buf, t_bar + BEAT * 0.6,  synth_lute_course(sixth_f,   ring_dur=1.4, vol=0.22, sr=sr), pan=pan)
            mix_note(left_buf, right_buf, t_bar + BEAT,        synth_lute_course(root_f,    ring_dur=3.0, vol=0.30, sr=sr), pan=pan)
            mix_note(left_buf, right_buf, t_bar + BEAT + 0.04, synth_lute_course(fifth_f,   ring_dur=2.8, vol=0.24, sr=sr), pan=pan)
            mix_note(left_buf, right_buf, t_bar + BEAT + 0.08, synth_lute_course(oct_f,     ring_dur=2.7, vol=0.24, sr=sr), pan=pan)
        else:
            mix_note(left_buf, right_buf, t_bar,               synth_lute_course(scale[1],  ring_dur=1.5, vol=0.25, sr=sr), pan=pan)
            mix_note(left_buf, right_buf, t_bar + BEAT,        synth_lute_course(root_f,    ring_dur=3.0, vol=0.30, octave_course=True, sr=sr), pan=pan)
            mix_note(left_buf, right_buf, t_bar + BEAT + 0.05, synth_lute_course(fifth_f,   ring_dur=2.8, vol=0.25, sr=sr), pan=pan)
        return t_bar + (MEASURE * 2.0)

    # 4. Currier B Signature (-edy / -ody / -dy) -> 3-Beat "Tempus Perfectum" Division
    if s in ("edy", "ody", "oldy", "aldy", "ordy", "dy"):
        mix_note(left_buf, right_buf, t_attack,         synth_lute_course(base_freq,  ring_dur=1.6, vol=0.26, sr=sr), pan=pan)
        mix_note(left_buf, right_buf, t_bar + BEAT,     synth_lute_course(third_freq, ring_dur=1.5, vol=0.22, sr=sr), pan=pan)
        mix_note(left_buf, right_buf, t_bar + BEAT * 2, synth_lute_course(fifth_freq, ring_dur=1.6, vol=0.25, sr=sr), pan=pan)
        return t_bar + MEASURE

    # 5. Liquid Suffixes (-ol, -or, -al, -ar) -> Trochaic Long-Short (Beat 1 + Beat 3)
    if s in ("ol", "or", "al", "ar"):
        mix_note(left_buf, right_buf, t_attack,         synth_lute_course(base_freq, ring_dur=1.8, vol=0.27, sr=sr), pan=pan)
        mix_note(left_buf, right_buf, t_bar + BEAT * 2, synth_lute_course(step_freq, ring_dur=1.5, vol=0.23, sr=sr), pan=pan)
        return t_bar + MEASURE

    # 6. Currier A Signature (-aiin / -iin) -> Strummed Double-Course Fifth Dyad + Beat 3 Echo
    if s in ("aiin", "aiir", "aiil", "iin"):
        mix_note(left_buf, right_buf, t_attack,         synth_lute_course(base_freq,  ring_dur=2.3, vol=0.28, sr=sr), pan=pan)
        mix_note(left_buf, right_buf, t_attack + 0.032, synth_lute_course(fifth_freq, ring_dur=2.1, vol=0.22, sr=sr), pan=pan)
        if is_discant:
            mix_note(left_buf, right_buf, t_bar + BEAT * 2, synth_lute_course(third_freq, ring_dur=1.4, vol=0.18, sr=sr), pan=pan)
        return t_bar + MEASURE

    # 7. Default Suffixes -> Grounded Downbeat Pluck
    mix_note(left_buf, right_buf, t_attack,
             synth_lute_course(base_freq, ring_dur=1.9, vol=0.26, octave_course=(not is_discant and deg <= 1), sr=sr),
             pan=pan)
    return t_bar + MEASURE

def render_tactus_duo(lines_a, lines_b, sr=44100):
    left_buf = []
    right_buf = []
    t_cursor = 0.25

    for idx in range(min(len(lines_a), len(lines_b))):
        ln_a = lines_a[idx]
        ln_b = lines_b[idx]
        n_bars = max(len(ln_a), len(ln_b))

        for bar_i in range(n_bars):
            is_last = (bar_i == n_bars - 1)
            pos = "START" if bar_i == 0 else ("END" if is_last else "MID")
            w_a = ln_a[min(bar_i, len(ln_a) - 1)]
            w_b = ln_b[min(bar_i, len(ln_b) - 1)]

            next_t_a = schedule_word_tactus(left_buf, right_buf, t_cursor, w_a, pos, DISCANT_SCALE, is_discant=True, sr=sr)
            next_t_b = schedule_word_tactus(left_buf, right_buf, t_cursor, w_b, pos, TENOR_SCALE,   is_discant=False, sr=sr)
            t_cursor = max(next_t_a, next_t_b)

    return left_buf, right_buf

def load_full_training_corpus(path: str):
    by_lang = {"A": [], "B": []}
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
            if len(words) >= 4 and curr_lang in ("A", "B"):
                by_lang[curr_lang].append(words)
    return by_lang

def save_stereo_wav(filename, left_buf, right_buf, sr=44100):
    peak = max(
        max((abs(x) for x in left_buf), default=1.0),
        max((abs(x) for x in right_buf), default=1.0),
        1e-6
    )
    gain = 0.90 / peak if peak > 0.90 else 1.0

    with wave.open(filename, "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for l_val, r_val in zip(left_buf, right_buf):
            l_int = int(max(-0.98, min(0.98, l_val * gain)) * 32767)
            r_int = int(max(-0.98, min(0.98, r_val * gain)) * 32767)
            frames.extend(struct.pack("<hh", l_int, r_int))
        wf.writeframes(frames)

if __name__ == "__main__":
    corpus_path = sys.argv[1] if len(sys.argv) > 1 else "LSI_ivtff_0d.txt"
    num_lines   = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    seed_val    = int(sys.argv[3]) if len(sys.argv) > 3 else int(time.time())

    rng = random.Random(seed_val)

    if os.path.exists(corpus_path):
        print(f"[*] Training VoynichCompilerV2 on full Takahashi ';H>' corpus '{corpus_path}'...")
        train_data = load_full_training_corpus(corpus_path)
    else:
        print("[!] Corpus file not found; training VoynichCompilerV2 on built-in seed lines...")
        train_data = {
            "A": [
                "fachys.ykal.ar.ataiin.shol.shory.cthres.y.kor.sholdy".split("."),
                "shol.chol.shoky.okol.sho.chol.chol.chal".split("."),
                "qokaiin.qokcho.shol.daiin.ckhear.ckhol.daiin.chkear".split("."),
                "dor.or.chain.dain.ykolody.ytaiin.qotchol.kol.dy".split("."),
                "pchor.chor.shol.cthol.qokol.daiin.shol.chor.oky.am".split("."),
                "tchol.shol.kol.chol.daiin.qokor.shol.kal.or.aiin".split(".")
            ],
            "B": [
                "qokedy.cheos.ytedy.qokedy.ytedy.chekedy.daiin.odam".split("."),
                "deeol.eeeody.qoteedy.qokody.qotedy.qotedy.opchedy.ofchy.chs.ar".split("."),
                "qkor.shedy.shey.keedy.sal.raiin.opchdy.dar.chedy.qopchedy.rorol".split("."),
                "polor.sheedy.okeedey.sal.aiin.sheedar.okedy.qopchedy.dalkedy.am".split("."),
                "pchedy.qokedy.qotedy.shedy.chedy.qokedy.okal.shedy.qokedy.am".split("."),
                "tchedy.otedy.okedy.qokeedy.shedy.qokedy.cheedy.okedy.dar.am".split(".")
            ]
        }

    comp_a = VoynichCompilerV2()
    comp_b = VoynichCompilerV2()
    comp_a.train(train_data["A"])
    comp_b.train(train_data["B"])

    print(f"[*] Compiling {num_lines} procedural duet lines (Random Seed: {seed_val})...")
    gen_a, gen_b = generate_procedural_duet_score(comp_a, comp_b, num_lines=num_lines, rng=rng)

    print("\n" + "=" * 74)
    print(f"  PROCEDURALLY COMPILED VOYNICH DUET SCORE (Seed: {seed_val})")
    print("=" * 74)
    for i in range(num_lines):
        print(f"  Line {i+1:02d} [Discant A] : {'.'.join(gen_a[i])}")
        print(f"          [Tenor   B] : {'.'.join(gen_b[i])}")
        print("-" * 74)

    print("\n[*] Plucking 15th-Century Karplus-Strong Lute Duo in Tempus Perfectum...")
    left, right = render_tactus_duo(gen_a, gen_b)
    out_file = f"voynich_procedural_lute_seed_{seed_val}.wav"
    save_stereo_wav(out_file, left, right)
    dur_sec = round(len(left) / 44100, 1)
    print(f"[✓] Saved Procedural Lute Duet: '{out_file}' ({dur_sec}s)")
    print(f"    (Tip: Re-run with `{seed_val}` as the 3rd argument to replay this exact duet!)")