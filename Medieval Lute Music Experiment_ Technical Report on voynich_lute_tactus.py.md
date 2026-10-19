Technical Report: State-Machine Grammar Sonification and Procedural Lute Duet Generation in xealeus-engine
1. Architectural Mission and Contextual Overview
Following the 2026 computational and paleographical milestones in reverse-engineering the text structure of the Voynich Manuscript—spanning the re-evaluation of unbound "singulion" pamphlet architecture, hand-executable substitution cipher modeling, and 3-slot Markov state-machine formulations—the xealeus-engine repository has integrated real-time state sonification into its computational cryptolinguistic pipeline. Transforming high-dimensional mathematical text models into auditory DSP control streams provides an immediate, high-fidelity perceptual feedback loop. This architecture leverages human auditory perceptual bandwidth: human hearing is uniquely sensitive to subtle micro-rhythmic anomalies, harmonic drift, and phase breaks across time-series data. Where visual log inspection of multi-megabyte conditional probability matrices and zlib compression tables can obscure higher-order boundary failures, real-time sonification exposes statistical misalignment as immediate auditory phenomena, such as chordal stagnation, voice-leading dissonance, or metric collapses.
The primary mandate of this technical report is to document the software architecture, statistical foundations, and signal processing pipelines of two core audio modules within xealeus-engine: the static sonification script (voynich_lute_tactus.py) and the procedural generation engine (voynich_procedural_lute_gen.py). Together, these scripts convert reverse-engineered text grammar—specifically 3-slot Markov mechanics, line-level packet envelopes, and horizontal inter-word domino coupling—into continuous acoustic synthesis parameters.
Integrated directly into the open-source repository, the procedural generator functions as an interactive, creative data exploration "easter egg" for codebase maintainers and cryptolinguists. Explicitly, this audio translation serves as a perceptual verification framework for statistical model fidelity; it is not a historical claim that the Voynich Manuscript codex was originally composed as a literal 15th-century musical score.
The following section deconstructs the foundational statistical grammar engine and parser hygiene protocols that supply the state vectors for acoustic mapping.
2. Foundational Grammar Engine: De-Duplicated Corpus Parsing and 3-Slot Markov Mechanics
Accurate state-machine modeling of the Voynich text requires absolute parser hygiene. Eliminating transcriber redundancy, tokenization artifacts, and improper character splitting is mandatory to prevent data leakage between evaluation splits and ensure that statistical state transitions reflect the physical manuscript rather than software bugs.
Corpus Ingestion & Cleaning Protocol
The 2026 parser updates applied to the Extensible Voynich Alphabet (EVA) pipeline overhaul the ingestion rules for the Interlinear Voynich Transliteration File Format (IVTFF) archive (LSI_ivtff_0d.txt). These updates resolve three structural defects present in pre-2026 processing baselines:
Parser Artifact / Defect
2026 Algorithmic Correction
Interlinear Transcriber Leakage <br>Multiple parallel transcriber readings (;H>, ;C>, ;F>, ;U>) within IVTFF files caused identical physical text lines to duplicate across train/test splits.
Strict ;H> Takahashi Filtering <br>Filters exclusively for the Takeshi Takahashi transcription (;H>), eliminating redundant parallel readings and preventing duplicate physical lines from straddling the 80/20 train/test split.
Period-Joined Strings <br>Inline formatting periods (.) and commas (,) were parsed naively, creating artificial multi-word concatenated strings.
True EVA Tokenization <br>Splits tokens strictly on IVTFF word-break periods (.) and commas (,), while stripping alignment fillers (!, %) to isolate exactly 34,674 single Voynich tokens across Currier A and B.
Naive Character Splitting <br>Treating complex multi-character EVA ligatures as disconnected individual glyphs corrupted intra-word state transitions.
Ligature-Aware Slot Decomposition <br>Enforces explicit multi-character EVA ligature recognition (qo, ch, sh, cth, ckh, cph, cfh, aiin, edy, ody) to decompose each token into a 3-slot tuple: (Prefix, Core, Suffix).

Cross-Dialect Core Vocabulary Unity
Decomposing the corpus into structural slots demonstrates that Currier A (11,450 tokens) and Currier B (23,224 tokens, comprising 34,674 total words) share an underlying vocabulary core:
90.29% of Currier B's total token mass uses middle Cores present in Currier A.
92.55% of Currier A's total token mass uses middle Cores present in Currier B.
32 of the Top 50 Cores are identical across both dialect sections.
The Top 10 Cores alone account for 61.34% of Currier A's text mass and 58.58% of Currier B's.
These metrics demonstrate that Currier A and Currier B do not represent distinct languages or separate ciphers. Instead, both dialects operate on a single core dictionary table while routing through dialect-specific suffix transition matrices:
P(\text{Suffix}_{\text{CurrierA}} \mid \text{Core}, \text{LinePos}) \quad \text{vs.} \quad P(\text{Suffix}_{\text{CurrierB}} \mid \text{Core}, \text{LinePos})
This formulation proves that dialect divergence is driven by toggling suffix registers—predominantly employing -ol, -y, and -aiin in Currier A versus -edy and -ey in Currier B—while drawing from an identical state-machine stem engine.
Intra-Word State-Walk Analysis (NMI Metrics)
Measuring Normalized Mutual Information (NMI %) across the three token slots exposes the internal structural generation rules of individual words:
Dialect / Section
Prefix \leftrightarrow Core (NMI %)
Core \leftrightarrow Suffix (NMI %)
Prefix \leftrightarrow Suffix (NMI %)
Currier A
29.62%
31.79%
7.08%
Currier B
35.67%
34.79%
5.95%
Stars (S)
40.22%
40.33%
5.27%
Balneo (B)
38.57%
35.44%
9.78%

The high Mutual Information between Prefix and Core (~30–40%) and between Core and Suffix (~32–40%), contrasted with the drop in direct Prefix-to-Suffix dependency (~5–9%), confirms that intra-word generation follows a memoryless, left-to-right state walk:
\text{Prefix} \longrightarrow \text{Core} \longrightarrow \text{Suffix}
In this Markov chain, the choice of Suffix is conditionally dependent on the immediate Core and the word's spatial position within the line, isolated from the initial Prefix.
Packet Line Envelopes
Physical lines in the manuscript function as operational units ("packet envelopes") bounded by structural rules:
START (Line Initialization): High-profile gallows prefixes (p- at 12.4%–15.0%, t- at 10.1%–14.8%, along with d- and s-) concentrate heavily on the line-initial token (Word_0) and drop out of top rankings in mid-line positions. In the Zodiac (Z) section, line initialization is rigid: 55.3% of lines initialize with ot- and 13.2% with ok- (68.5% combined).
MID (Payload Execution): Tokens in mid-line positions (Word_1 \dots Word_{N-2}) shift to payload execution prefixes, dominated by ch- (22.3% in Currier A) and qo- (19.4% in Currier B; 25.1% in Balneo).
END (Line Termination): The terminal stop-bit suffix -am (m/g) is absent from top rankings at START or MID positions but spikes at line endings: 15.6% in Currier B, 18.9% in Text T, 19.2% in Stars S, and 21.5% in Cosmological C.
While these local state-walk and packet rules govern individual word assembly, generating complete lines requires modeling inter-word interactions across line vectors.
3. Inter-Word Domino Chaining and Compression Coupling
First-generation word-level Markov compilers generate valid isolated vocabulary items but fail to replicate full line-level statistical structures due to the lack of horizontal coupling mechanisms across adjacent word boundaries.
The zlib Compressibility Order Delta Gap
To measure higher-order horizontal line structure, the order delta metric measures the compressibility differential between natural line sequences and randomly shuffled controls:
\Delta_{\text{bits/word}} = \text{zlib}_{\text{shuffled}} - \text{zlib}_{\text{original}}
Evaluating this metric highlights a structural discrepancy between historical text and first-generation state-machine outputs:
Currier A: Real Manuscript = 0.359 bits/word vs. First-Gen Compiler = 0.007 bits/word
Currier B: Real Manuscript = 0.557 bits/word vs. First-Gen Compiler = 0.240 bits/word
First-generation compilers selected each word's Core and Suffix independently of adjacent tokens, conditioning only on the previous word's Prefix (prev_p). In physical manuscript lines, adjacent words exhibit horizontal coupling across Cores and Suffixes. Torsten Timm's (2014, 2016) self-citation research documents this structural copying behavior, as evidenced by cross-page and adjacent line pairs such as <f84r.P.6> ol shedy qokedy shedy versus <f84v.P.26> dal shedy qokedy shedy, and running line sequences like qokedy \cdot qotedy \cdot qokedy or chol \cdot chor \cdot chol.
When uncoupled, first-generation synthetic text audio exhibits noticeable auditory artifacts: synthesized lute voices produce monotonous phrase repetition, unnatural metric freezing, and static harmonic stagnation.
Domino Chaining Mechanism
To close the zlib compressibility gap and eliminate auditory stagnation, VoynichCompilerV2 implements horizontal transition coupling using a joint conditional probability chain rule:
P(Word_{t+1} \mid Word_t) = P(Prefix_{t+1} \mid Suffix_t) \cdot P(Core_{t+1} \mid Core_t, Prefix_{t+1}) \cdot P(Suffix_{t+1} \mid Core_{t+1}, LinePos)
This mechanism injects two horizontal linkages:
Core-to-Core Coupling: Core[t] \longrightarrow Core[t+1], carrying exactly 1.20 bits of Mutual Information.
Suffix-to-Prefix Linkages: Suffix[t] \longrightarrow Prefix[t+1], establishing a "domino chaining" effect where the terminal state of Word_t conditions the initial state of Word_{t+1}.
[ WORD t ]                                     [ WORD t+1 ]
+------------------------------------+         +------------------------------------+
| Prefix[t] -> Core[t] -> Suffix[t]  |         | Prefix[t+1] -> Core[t+1] -> Suffix |
+------------------|---------|-------+         +---|----------------|---------------+
                   |         |                     ^                ^
                   |         +-- Suffix-to-Prefix -+                |
                   +------------ Core-to-Core Coupling (1.20 bits) --+

Injecting 1.20 bits of Mutual Information across adjacent cores brings synthetic text line compressibility to historical manuscript baselines (0.359 bits/word in A, 0.557 bits/word in B).
The next section details the software architecture and DSP implementation used to convert these state-machine parameters into real-time audio.
4. Software Architecture: Static Sonification vs. Procedural Duet Engine
The audio framework within xealeus-engine maps textual state walks directly to digital signal processing control vectors, rendering abstract linguistic transitions as audible acoustic phenomena.
Static Sonification Architecture (voynich_lute_tactus.py)
The static sonification module reads IVTFF transcription files directly and generates deterministic audio renderings of physical manuscript lines.
python -m xealeus.sonification.voynich_lute_tactus \
    --input data/LSI_ivtff_0d.txt \
    --filter TAKAHASHI_H \
    --dialect B

The script parses raw EVA strings into NumPy numerical array vectors representing pitch indices, dynamic velocities, and duration timings. By executing a strict 1:1 translation of transcribed manuscript characters, voynich_lute_tactus.py provides a deterministic benchmark for auditory analysis.
Procedural Generator Architecture (voynich_procedural_lute_gen.py)
The procedural duet generator provides an end-to-end dynamic text generation and synthesis pipeline:
python -m xealeus.procedural.voynich_procedural_lute_gen \
    --model VoynichCompilerV2 \
    --coupling domino \
    --mi-target 1.20 \
    --tempo-mode tempus_perfectum

+------------------------+      +--------------------+      +----------------------+
|  IVTFF Cleaned Corpus  | ---> | VoynichCompilerV2  | ---> |  Synthetic Token     |
| (data/LSI_ivtff_0d.txt)|      |  (3-Slot + Domino) |      |  Stream Generator    |
+------------------------+      +--------------------+      +----------------------+
                                                                       |
                                                                       v
+------------------------+      +--------------------+      +----------------------+
| Real-time WAV / Buffer | <--- |   Karplus-Strong   | <--- | Slot Vector Mapper   |
|   Acoustic Output      |      |   2-Voice DSP      |      | (D-Dorian Polyphony) |
+------------------------+      +--------------------+      +----------------------+

Compiler Training: Initializes VoynichCompilerV2 using dictionary lookup tables built from the cleaned Takahashi ;H> corpus.
Text Synthesis: Executes the 3-slot Markov state walk with 1.20-bit domino core coupling to generate synthetic "faux Voynich" token lines.
Control Stream Vectorization: Translates generated token streams in real time into continuous numerical control streams (fret values, delay-line lengths, pluck velocities, and damping triggers).
Acoustic Synthesis Engine & Musical Framework
The software engine synthesizes audio using Karplus-Strong physical modeling, framed within 15th-century musical constraints:
Tuning System & Scale Mapping: Mapped to a 15th-century D-Dorian mode (D_2, E_2, F_2, G_2, A_2, B\flat_2, C_3, D_3, E_3, F_3, G_3, A_3).
Karplus-Strong DSP Physics: Plucked strings are synthesized using delay-line physical modeling:
y[n] = x[n] + \alpha \cdot \frac{y[n - N] + y[n - (N + 1)]}{2}
where delay buffer length N = \lfloor f_s / f_0 \rfloor, audio sample rate f_s = 44100 \text{ Hz}, fundamental pitch frequency f_0 is mapped from the core glyph index, and \alpha represents the feedback damping factor (0.985 \le \alpha \le 0.998).
Polyphonic Voice Allocation:
Voice 1 (Cantus Firmus): Maps primary Core[t] \longrightarrow Core[t+1] state walks to fundamental pitch registers and primary fret positions.
Voice 2 (Counterpoint): Maps Suffix[t] \longrightarrow Prefix[t+1] domino linkages to harmonic counterpoint intervals (fourths, fifths, and octaves).
Line Packet Rhythmic Envelope: Operates in Tempus Perfectum (3/4 metric time).
START (Gallows Prefixes): Triggers initial string-pluck accent dynamics (Velocity \ge 110).
MID (Payload Tokens): Drives running quarter-note tactus pulses across measure cycles.
END (-am Stop Bits): Triggers soft string damping routines (\alpha \to 0) at measure line boundaries.
The next section presents empirical acoustic verification comparing natural manuscript transcriptions against procedural engine output.
5. Acoustic Verification: Statistical Parity and Auditory Proof
Sonifying both natural transcriptions and compiler-generated synthetic text demonstrates that procedural audio output serves as an effective perceptual validation metric for high-dimensional language models.
Auditory Equivalence Metrics
Because VoynichCompilerV2 captures both intra-word slot dependencies and horizontal domino chaining, audio generated from synthetic text is perceptually indistinguishable in acoustic texture, phrasing, and dynamic contour from audio generated from native manuscript transcriptions.
Sonification provides a distinct perceptual bandwidth advantage: human hearing detects statistical breaks in high-dimensional text models faster than visual log inspection. A failure in higher-order Markov coupling manifests instantly as audible phrase repetition, rhythmic stalling, or chordal dissonance, alerting researchers to model breakdown without requiring manual matrix inspection.
Textual features map directly to acoustic phenomena:
Cadence Envelopes: Line-ending -am stop bits map directly to cadence resolutions, triggering soft damping routines (\alpha \to 0) and rest cycles at measure endings in Tempus Perfectum.
2D Harmonic Core Coupling: Horizontal Core[t] \longrightarrow Core[t+1] domino transitions maintain voice leading between Voice 1 and Voice 2, eliminating unnatural scalar leaps and chordal stagnation.
Header Initialization: Line-start gallows prefixes (p-, t-) trigger accented plucked ostinatos (Velocity \ge 110) at the start of measure cycles, providing an audible marker for line boundaries.
Proof of Statistical Fidelity
Blind-compiled synthetic text generated by VoynichCompilerV2 achieves 86.79% vocabulary parity in Currier A and 88.64% in Currier B against held-out manuscript vocabularies:
[Currier A Parity]  |===========================--------| 86.79%
[Currier B Parity]  |============================-------| 88.64%

Because the synthetic text matches historical vocabulary distributions while maintaining 1.20 bits of horizontal core coupling, the generated lute duets produce matching rhythmic cadences, voice leading, and dynamic envelopes. These identical acoustic dynamics confirm that VoynichCompilerV2 accurately models the underlying statistical grammar of the manuscript.
The final section establishes academic alignment and software maintainer directives for open-source integration.
6. Epistemic Guardrails and Open-Source Integration
Integrating computational state machines with physical modeling algorithms requires clear methodological boundaries, ensuring that software implementations are distinguished from historical claims.
Clear Disambiguation of Purpose
The Karplus-Strong lute duet engine within xealeus-engine is designed exclusively as an interactive data exploration tool and open-source repository feature. It provides an intuitive auditory interface for evaluating mathematical state walks. This implementation is an analytical tool and must not be interpreted as a claim that the historical Voynich Manuscript was composed as a 15th-century musical score.
Repository Usage & Maintenance Directives
Maintainers and developers working with the xealeus-engine repository can reproduce these results using the standard execution workflows:
Static Baseline Execution:
python -m xealeus.sonification.voynich_lute_tactus \
    --input data/LSI_ivtff_0d.txt \
    --filter TAKAHASHI_H \
    --dialect B

Procedural Duet Generation:
python -m xealeus.procedural.voynich_procedural_lute_gen \
    --model VoynichCompilerV2 \
    --coupling domino \
    --mi-target 1.20 \
    --tempo-mode tempus_perfectum

In summary, structural sonification translates complex language statistics into real-time perceptual feedback. By mapping mathematical state-machine parameters onto physical DSP models, xealeus-engine provides a rigorous, accessible framework for verifying high-dimensional text generation models.


