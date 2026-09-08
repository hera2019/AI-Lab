# Phase 1–2 baseline

## Why these tests exist

The 2-step smoke test checks whether the entire local video pipeline can finish. It is not a quality test. The 12-step test asks whether a minimally useful image structure begins to appear without changing the model, prompt, seed, resolution, or frame count.

## Common setup

- Model: Wan2.2 TI2V 5B `Q4_K_M`
- Text encoder: UMT5-XXL `Q5_K_M`
- VAE: full Wan2.2 VAE in FP16
- Runtime: stable-diffusion.cpp `6b3edaaf32cc19e5bb2d819c788bd557eddc8eba`
- Backend: Apple Metal
- Size: 416×256 pixels
- Length: 17 frames at 24 fps (container duration 0.667 seconds)
- Sampler: Euler
- CFG: 6.0
- Flow shift: 3.0
- Seed: 260905

## 2-step smoke test

- Conditioning: 13.42 seconds
- Sampling: 10.29 seconds
- VAE decode: 342.17 seconds
- Video generation: 365.93 seconds
- Wall time: 367.18 seconds
- Maximum resident set size: 15,035,842,560 bytes (14.00 GiB)
- Swaps reported by `/usr/bin/time`: 0
- Output: VP8 WebM, 416×256, 24 fps, 39,524 bytes
- Visual result: an orange blurred field; no reliable boat, bowl, or table structure.

Conclusion: the full pipeline, Metal backend, VAE decode, and video writer work. Two steps are insufficient for a quality judgement.

## 12-step quality baseline

- Conditioning: 10.22 seconds
- Sampling: 42.03 seconds
- VAE decode: 344.64 seconds
- Video generation: 396.93 seconds
- Wall time: 398.18 seconds
- Maximum resident set size: 15,360,786,432 bytes (14.31 GiB)
- Swaps reported by `/usr/bin/time`: 0
- Output: VP8 WebM, 416×256, 24 fps, 187,273 bytes
- Visual result: glass-like forms, a warm wooden scene, and small inter-frame changes appear. The requested red toy sailboat is not reliably formed; the result remains abstract and oversaturated.

Conclusion: 12 steps materially improve structure, but this prompt and resolution do not yet give a usable result. VAE decode is the dominant cost and is effectively unchanged by the sampling-step count.

## 20-step simple-prompt control

- Conditioning: 10.01 seconds
- Sampling: 64.86 seconds
- VAE decode: 329.30 seconds
- Video generation: 404.21 seconds
- Wall time: 405.49 seconds
- Maximum resident set size: 15,154,905,088 bytes (14.11 GiB)
- Swaps reported by `/usr/bin/time`: 0
- Visual result: coherent blue/white color regions but no reliable sailboat; the output remains blocky and garbled.

Conclusion: the failure is not explained by too few steps or the original multi-material prompt. Existing stable-diffusion.cpp community reports reproduce garbled Wan2.2 TI2V 5B output around 416×240 even with Q8 and varied sampling settings. The controlled next test therefore raises spatial resolution rather than changing quantization.

## Next controlled test

Generate a single 832×480 frame at 20 steps. If it is coherent, proceed to a 17-frame 832×480 video; if not, compare Q8/FP16 or investigate the runtime.
