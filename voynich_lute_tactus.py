#!/usr/bin/env python3
"""
voynich_lute_tactus.py — 15th-Century Lute Duo in "Tempus Perfectum" (3/4 Tactus)
=================================================================================
Upgrades the Voynich Karplus-Strong Lute Duo with authentic early-1400s
rhythmic mensuration ("Tempus Perfectum" / Basse Danse 3-beat tactus),
synchronized barlines between Currier A (Discant) and Currier B (Tenor),
medieval Landini cadences on the `-am` stop bit, and a built-in waveform inspector.

Usage:
    python3 voynich_lute_tactus.py [LSI_ivtff_0d.txt] [num_duet_lines]
"""

import sys
import os
import re
import math
import random
import wave
import struct

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

# Tempus Perfectum (3 Semibreves per Breve / 3-Beat Medieval Tactus)
# 1 Beat (Minima) = 0.28s (~107 BPM pulse -> 1 Measure of 3 beats = 0.84s)
BEAT = 0.28
MEASURE = BEAT * 3.0  # 0.84s per word-measure (Long-Short trochaic lilt)

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

def core_to_degree(core: str) -> int:
    if core in CORE_TO_DEGREE:
        return CORE_TO_DEGREE[core]
    return sum(ord(c) for c in core) % 7

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
    """
    Schedules one Voynich word into a strict 15th-century 3-Beat "Tempus Perfectum"
    measure (`MEASURE = 3 * BEAT = 0.84s`), so Discant and Tenor stay rhythmically locked!
      - Beat 1 (0.00): Downbeat (Long / Breve pulse)
      - Beat 2 (BEAT): Middle division
      - Beat 3 (2*BEAT): Upbeat / Trochaic short step
    """
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

    # 2. Ring/Zodiac Prefix (ot-, ok-) -> Medieval Plectrum Grace-Note Flick before Beat 1
    t_attack = t_bar
    if p in ("ot", "ok"):
        mix_note(left_buf, right_buf, t_bar,
                 synth_lute_course(third_freq, ring_dur=1.1, vol=0.19, sr=sr),
                 pan=pan)
        t_attack = t_bar + (BEAT * 0.35)

    # 3. Line-End Stop Bit (-am or END) -> 15th-Century "Landini Cadence" (2 Full Measures = 6 Beats)
    #    Beat 1: Subtonic 7th (C) -> Beat 2: 6th (B) -> Beat 3: Rolled Root-Fifth-Octave Chord (D-A-D)!
    if s == "am" or pos == "END":
        seventh_f = scale[6]  # C
        sixth_f   = scale[5]  # B (Landini under-third step)
        root_f    = scale[0]  # D (Finalis)
        fifth_f   = scale[4]  # A (Confinalis)
        oct_f     = scale[0] * 2.0

        if is_discant:
            # Discant plays the ornamental Landini 7 -> 6 -> 8 cadence melody
            mix_note(left_buf, right_buf, t_bar,              synth_lute_course(seventh_f, ring_dur=1.4, vol=0.24, sr=sr), pan=pan)
            mix_note(left_buf, right_buf, t_bar + BEAT * 0.6, synth_lute_course(sixth_f,   ring_dur=1.4, vol=0.22, sr=sr), pan=pan)
            mix_note(left_buf, right_buf, t_bar + BEAT,       synth_lute_course(root_f,    ring_dur=3.0, vol=0.30, sr=sr), pan=pan)
            mix_note(left_buf, right_buf, t_bar + BEAT + 0.04, synth_lute_course(fifth_f,  ring_dur=2.8, vol=0.24, sr=sr), pan=pan)
            mix_note(left_buf, right_buf, t_bar + BEAT + 0.08, synth_lute_course(oct_f,    ring_dur=2.7, vol=0.24, sr=sr), pan=pan)
        else:
            # Tenor holds the descending 2nd (E) -> Root (D) open fifth cadence
            mix_note(left_buf, right_buf, t_bar,              synth_lute_course(scale[1],  ring_dur=1.5, vol=0.25, sr=sr), pan=pan)
            mix_note(left_buf, right_buf, t_bar + BEAT,       synth_lute_course(root_f,    ring_dur=3.0, vol=0.30, octave_course=True, sr=sr), pan=pan)
            mix_note(left_buf, right_buf, t_bar + BEAT + 0.05, synth_lute_course(fifth_f,  ring_dur=2.8, vol=0.25, sr=sr), pan=pan)
        return t_bar + (MEASURE * 2.0)

    # 4. Currier B Signature (-edy / -ody / -dy) -> 3-Beat "Tempus Perfectum" Division (Beats 1, 2, 3)
    if s in ("edy", "ody", "oldy", "aldy", "ordy", "dy"):
        mix_note(left_buf, right_buf, t_attack,          synth_lute_course(base_freq,  ring_dur=1.6, vol=0.26, sr=sr), pan=pan)
        mix_note(left_buf, right_buf, t_bar + BEAT,      synth_lute_course(third_freq, ring_dur=1.5, vol=0.22, sr=sr), pan=pan)
        mix_note(left_buf, right_buf, t_bar + BEAT * 2,  synth_lute_course(fifth_freq, ring_dur=1.6, vol=0.25, sr=sr), pan=pan)
        return t_bar + MEASURE

    # 5. Liquid Suffixes (-ol, -or, -al, -ar) -> Classic Medieval "Trochaic" Long-Short (Beat 1 [2 beats] + Beat 3 [1 beat])
    if s in ("ol", "or", "al", "ar"):
        mix_note(left_buf, right_buf, t_attack,          synth_lute_course(base_freq, ring_dur=1.8, vol=0.27, sr=sr), pan=pan)
        mix_note(left_buf, right_buf, t_bar + BEAT * 2,  synth_lute_course(step_freq, ring_dur=1.5, vol=0.23, sr=sr), pan=pan)
        return t_bar + MEASURE

    # 6. Currier A Signature (-aiin / -iin) -> Strummed Double-Course Fifth Dyad on Beat 1 + Gentle Echo on Beat 3
    if s in ("aiin", "aiir", "aiil", "iin"):
        mix_note(left_buf, right_buf, t_attack,          synth_lute_course(base_freq,  ring_dur=2.3, vol=0.28, sr=sr), pan=pan)
        mix_note(left_buf, right_buf, t_attack + 0.032,  synth_lute_course(fifth_freq, ring_dur=2.1, vol=0.22, sr=sr), pan=pan)
        if is_discant:
            mix_note(left_buf, right_buf, t_bar + BEAT * 2, synth_lute_course(third_freq, ring_dur=1.4, vol=0.18, sr=sr), pan=pan)
        return t_bar + MEASURE

    # 7. Default Suffixes (-y, -ey, etc.) -> Grounded Downbeat Pluck (Full 3-Beat Measure)
    mix_note(left_buf, right_buf, t_attack,
             synth_lute_course(base_freq, ring_dur=1.9, vol=0.26, octave_course=(not is_discant and deg <= 1), sr=sr),
             pan=pan)
    return t_bar + MEASURE

def render_tactus_duo(lines_a, lines_b, sr=44100):
    """
    Locks Currier A (Discant Lute) and Currier B (Tenor Lute) to the exact same
    3-Beat Tactus Measure Grid word-for-word, so their rhythms interlock like gears!
    """
    left_buf = []
    right_buf = []
    t_cursor = 0.25

    n_pairs = min(len(lines_a), len(lines_b))
    for idx in range(n_pairs):
        ln_a = lines_a[idx]
        ln_b = lines_b[idx]
        n_bars = max(len(ln_a), len(ln_b))

        for bar_i in range(n_bars):
            is_last = (bar_i == n_bars - 1)
            pos = "START" if bar_i == 0 else ("END" if is_last else "MID")

            # Pick current word in A and B (if one line is shorter, repeat its final cadence token on END)
            w_a = ln_a[min(bar_i, len(ln_a) - 1)]
            w_b = ln_b[min(bar_i, len(ln_b) - 1)]

            next_t_a = schedule_word_tactus(left_buf, right_buf, t_cursor, w_a, pos, DISCANT_SCALE, is_discant=True, sr=sr)
            next_t_b = schedule_word_tactus(left_buf, right_buf, t_cursor, w_b, pos, TENOR_SCALE,   is_discant=False, sr=sr)

            t_cursor = max(next_t_a, next_t_b)

    return left_buf, right_buf

def inspect_waveform(left_buf, right_buf, sr=44100, bins=48):
    """Prints an acoustic waveform & stereo envelope inspection table to the terminal."""
    n = min(len(left_buf), len(right_buf))
    dur = n / sr
    step = max(1, n // bins)

    rms_l = math.sqrt(sum(x * x for x in left_buf[:n]) / max(1, n))
    rms_r = math.sqrt(sum(x * x for x in right_buf[:n]) / max(1, n))
    peak = max(max(abs(x) for x in left_buf[:n]), max(abs(x) for x in right_buf[:n]), 1e-6)
    crest_db = 20.0 * math.log10(peak / max(1e-6, (rms_l + rms_r) * 0.5))

    print("\n" + "=" * 68)
    print("  WAVEFORM & ACOUSTIC ENVELOPE INSPECTION")
    print("=" * 68)
    print(f"  Duration        : {dur:.2f} sec ({n:,} stereo frames @ {sr} Hz)")
    print(f"  Tactus Meter    : Tempus Perfectum (3/4 Triple Meter, {BEAT*1000:.0f}ms pulse)")
    print(f"  Left RMS (Tenor): {rms_l:.4f} | Right RMS (Discant): {rms_r:.4f}")
    print(f"  Crest Factor    : {crest_db:.2f} dB (Authentic Plucked Transient Headroom)")
    print("-" * 68)
    print("  Time (s) | Stereo Waveform Amplitude Envelope (48 Windows)")
    print("-" * 68)

    bar_chars = " ▂▃▄▅▆▇█"
    ascii_strip = []
    for b in range(bins):
        chunk_l = left_buf[b * step : (b + 1) * step]
        chunk_r = right_buf[b * step : (b + 1) * step]
        if not chunk_l:
            continue
        loc_rms = math.sqrt(sum((l*l + r*r)*0.5 for l, r in zip(chunk_l, chunk_r)) / len(chunk_l))
        norm = min(1.0, loc_rms / max(1e-6, peak * 0.45))
        idx = min(len(bar_chars) - 1, int(norm * (len(bar_chars) - 1)))
        ascii_strip.append(bar_chars[idx])

    print("  0.0s     | " + "".join(ascii_strip) + f" | {dur:.1f}s")
    print("=" * 68 + "\n")

def load_lines(path: str, max_lines=10):
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
            if len(words) >= 5 and curr_lang in ("A", "B"):
                if len(by_lang[curr_lang]) < max_lines:
                    by_lang[curr_lang].append(words)
            if len(by_lang["A"]) >= max_lines and len(by_lang["B"]) >= max_lines:
                break
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
    num_lines = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    if os.path.exists(corpus_path):
        print(f"[*] Loading {num_lines} paired lines of Currier A & B from '{corpus_path}'...")
        data = load_lines(corpus_path, max_lines=num_lines)
    else:
        print("[!] Corpus file not found; using built-in Currier A & B duet lines...")
        data = {
            "A": [
                "fachys.ykal.ar.ataiin.shol.shory.cthres.y.kor.sholdy".split("."),
                "shol.chol.shoky.okol.sho.chol.chol.chal".split("."),
                "qokaiin.qokcho.shol.daiin.ckhear.ckhol.daiin.chkear".split("."),
                "dor.or.chain.dain.ykolody.ytaiin.qotchol.kol.dy".split(".")
            ],
            "B": [
                "qokedy.cheos.ytedy.qokedy.ytedy.chekedy.daiin.odam".split("."),
                "deeol.eeeody.qoteedy.qokody.qotedy.qotedy.opchedy.ofchy.chs.ar".split("."),
                "qkor.shedy.shey.keedy.sal.raiin.opchdy.dar.chedy.qopchedy.rorol".split("."),
                "polor.sheedy.okeedey.sal.aiin.sheedar.okedy.qopchedy.dalkedy.am".split(".")
            ]
        }

    print("[*] Synthesizing 15th-Century Lute Duo in Tempus Perfectum (3/4 Tactus)...")
    left, right = render_tactus_duo(data["A"], data["B"])
    inspect_waveform(left, right)
    out_file = "voynich_lute_tempus_perfectum.wav"
    save_stereo_wav(out_file, left, right)
    print(f"[✓] Saved synchronized 15th-Century Lute Duo: '{out_file}'")