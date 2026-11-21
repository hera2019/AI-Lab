# AI Lab

**Project pages:** [houjun.dev/lab](https://houjun.dev/lab/), one page per study, written for non-specialists.

Seven local-inference studies on a single 32 GB Apple Silicon machine.

This is **not a collection of model demos.** Every study answers the same three
questions:

> **Can this model ship? What does it cost? How does it fail?**

The recurring finding across all seven turned out to be a single idea:
**knowing what a passing result does *not* prove.** See
[What a passing result does not prove](#what-a-passing-result-does-not-prove).

*[中文版 / Chinese version](README.zh-CN.md)*

---

## Method

1. **Test plan first.** Each study starts from a written plan with acceptance
   criteria, before any model is downloaded.
2. **Two outputs per result.** A human-readable report (`.md`) and
   machine-readable metrics (`.json`) — so every number can be re-derived rather
   than trusted.
3. **"It runs" is separated from "it passes."** A working pipeline is never
   reported as a quality conclusion.
4. **Negative and unresolved results stay.** Nothing is retro-fitted once the
   answer is known; superseded conclusions are kept with the reason they failed.
5. **Reproducible by construction.** Pinned revisions, SHA-256 verification,
   fixed seeds. Model weights live outside the repository.

---

## Studies

| Study | Domain | Key finding |
|---|---|---|
| [whisper-large-v3-turbo](whisper-large-v3-turbo-whispercpp/) | Speech recognition | End-to-end captioning is **two** latencies, not one: 1.92 s to a settled transcript, 2.75 s including end-of-sentence confirmation. Pure silence hallucinates `Thank you.`; streaming VAD removes it. |
| [qwen3-tts-0.6b-voice-clone](qwen3-tts-0.6b-voice-clone-mlx/) | Speech synthesis | Runs at **0.842 RTF** (faster than real time) on this hardware — but long-form generation **silently skips text**: 17% of a passage was dropped in a way no listener can hear. |
| [qwen3-vl-8b](qwen3-vl-8b-llamacpp/) | Vision-language | On a real Japanese receipt: local model 16/17 strict business fields in ~11.2 s. Apple Vision was 3× faster and **perfectly consistent across runs — while confidently misreading a date.** Consistency is not correctness. |
| [qwen3-14b](qwen3-14b-llamacpp/) | Language model | Q4_K_M at ~8.38 GiB. Benchmarking settled the operating point: 8K context, reasoning off, Q8_0 KV cache for daily use; 16K for long documents. |
| [qwen3-embedding-0.6b](qwen3-embedding-0.6b-llamacpp/) | Retrieval | Title + body indexing reached **Recall@1 9/9 and Recall@3 9/9** across nine cross-language questions (zh / ja / en). |
| [wan2.2-ti2v-5b](wan2.2-ti2v-5b-stablediffusioncpp/) | Video generation | FastWan cut an 832×480 / 33-frame preview from **~7 minutes to ~1 minute** — the difference between an unusable and a usable iteration loop. |
| [flux2-klein-4b](flux2-klein-4b-stablediffusioncpp/) | Image generation | Text-to-image, image editing, multi-reference conditioning, text rendering and prompt adherence, plus error boundaries. |

---

## A representative finding

**The clone sounded right. It just didn't say everything.**

A 60-second voice-cloning test produced audio that was natural, well-paced and
recognisably the right speaker. It was also missing 40 characters from the
middle of the passage.

Nobody could hear it — because the skipped span still reads as a fluent
sentence. It just isn't the sentence in the source text.

It was found by disagreeing with the listening test: transcribing the output
back through two independent ASR systems and comparing against the source. Both
pointed at the same gap, which ruled out recognition error; the gap was in the
middle with the ending intact, which ruled out truncation.

The cause was in the text. The phrase *"我现在说……"* occurs three times in the
passage. Having read up to the first occurrence, the model resumed at the third
— a text-to-audio alignment slip on a repeated n-gram, the way a person reading
aloud skips to a similar line further down.

Three things followed:

- **A hypothesis died.** The model was not "capped at ~35 seconds" — it read to
  the very end. Generation length was never the limit; **alignment stability was.**
- **An engineering rule replaced it.** Generate sentence by sentence, and verify
  every output by transcribing it back. Neither alone is sufficient.
- **A class of risk got a name.** This is a *silent* failure: no error, no
  artefact, no gap in the audio. It cannot be caught by listening, only by
  cross-checking — which is the entire reason the round-trip check exists.

Full record: [`phase-1-iphone-repeat-verification.md`](qwen3-tts-0.6b-voice-clone-mlx/results/phase-1-iphone-repeat-verification.md)

---

## What a passing result does not prove

The same shape of mistake kept appearing in different domains. Collected here
because the pattern is more useful than any individual number:

| Domain | The tempting conclusion | What it actually proves |
|---|---|---|
| Speech synthesis | The program ran without error | Nothing about whether the voice is usable |
| Speech synthesis | It sounds like the right speaker | Nothing about whether the content is complete |
| Speech recognition | It produced fluent text | Nothing — silence produces fluent text too |
| Receipt OCR | Three runs agreed exactly | Nothing about correctness; it was consistently wrong |
| Voice cloning | Transcribing it back gives the right words | Nothing about whether the timbre matches |
| Speaker turns | Turns were segmented correctly | Nothing about *who* those speakers are |

Every one of these was reached by building the check that could disagree with
the result — a second ASR system, a strict field-by-field ground truth, a
listener who knows the speaker. **The check is the deliverable.**

---

## Hardware and environment

| | |
|---|---|
| Machine | Mac Studio · Apple M2 Max · 32 GB Unified Memory |
| OS | macOS 26.6.2, arm64 |
| Runtimes | llama.cpp · whisper.cpp · stable-diffusion.cpp · MLX / MLX-Audio |
| Acceleration | Apple Metal, Apple Accelerate |

Everything runs offline. No inference in these studies depends on a network
service.

Model weights are **not** in this repository — they are downloaded to a separate
directory by each study's `scripts/download_*` with a pinned revision and
SHA-256 verification. Several studies deleted their weights on completion; the
records remain complete without them.

---

## Ethics and privacy

This repository contains research on both speech recognition and speech
synthesis, including voice cloning. That combination deserves an explicit
boundary.

- **No human voice recordings are published here** — not even the author's own.
  Publishing them alongside cloning tooling would supply both a voiceprint and
  the method, so the whole category is excluded regardless of content.
- Audio fixtures that *are* published are **synthetic**, generated with
  `macOS say` + FFmpeg, and documented as such in
  [`manifest.json`](whisper-large-v3-turbo-whispercpp/tests/fixtures/audio/manifest.json).
- Voice cloning is gated in code, not in documentation:
  [`clone_voice.py`](qwen3-tts-0.6b-voice-clone-mlx/scripts/clone_voice.py)
  refuses to run without `--consent-confirmed`, and every result carries
  `synthetic_audio: true` and a `consent` field in its metadata.
- Verbatim transcripts of the author's own recordings are redacted before
  publication by
  [`tools/redact_for_publication.py`](tools/redact_for_publication.py). All
  objective metrics — duration, sample rate, RTF, memory, seed, SHA-256 — are
  preserved untouched, so no finding depends on the redacted text.

Generated audio is never presented as a real person.

---

## Reading this repository

Each study is self-contained and follows the same layout:

```
<study>/
├── README.md          goal, boundaries, current status
├── docs/NN-plan.md    the test plan, written first
├── results/
│   ├── phase-N.md     conclusions, including subjective checks
│   ├── phase-N.json   raw metrics
│   └── phase-N.log    full run output
├── scripts/           runnable, parameterised by environment variable
└── tests/fixtures/    synthetic test material with a manifest
```

Individual study READMEs are written in Chinese; results tables, metrics and
code are language-independent.

If you only read one thing, read
[the voice-cloning verification record](qwen3-tts-0.6b-voice-clone-mlx/results/phase-1-iphone-repeat-verification.md)
— it is the shortest complete example of how these studies work: a suspicion, a
cross-check that could have proved it wrong, a located root cause, and a rule
derived from it.

---

## License

[Apache-2.0](LICENSE)
