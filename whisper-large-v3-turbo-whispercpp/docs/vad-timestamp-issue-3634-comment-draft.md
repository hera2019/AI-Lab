# Draft follow-up for whisper.cpp Issue #3634

Target: https://github.com/ggml-org/whisper.cpp/issues/3634

Please review, rewrite in your own voice, and verify every claim before posting.

---

I can still reproduce this class of problem on current `master`, commit `eacbd8234c6654cdbf2c377f72b2106875479bdc` (`1.9.3-dev`). I used only the repository's `samples/jfk.wav`: three copies concatenated with 2 seconds of generated silence between them.

The copies begin at 0.000, 13.000, and 26.000 seconds. Silero v6.2.0 reports the first speech in each copy at 0.320, 13.310, and 26.310 seconds, so the VAD locations themselves are correct.

With `ggml-large-v3-turbo-q5_0.bin`, the SRT cue starts were:

| copy | audio starts | first VAD speech | SRT without VAD | SRT with VAD |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.000 | 0.320 | 0.000 | 0.320 |
| 2 | 13.000 | 13.310 | 12.840 | **10.370** |
| 3 | 26.000 | 26.310 | 25.840 | **24.940** |

All three cues contain the correct repeated JFK sentence. The second VAD-enabled cue therefore begins 2.630 seconds before its source copy starts, and the third begins 1.060 seconds early, inside the 24–26 second silent gap. Greedy decoding (`--beam-size 1 --best-of 1`) gives essentially the same 10.350 and 24.940 starts.

As a model comparison, `ggml-base.en.bin` does not produce the early starts: its VAD-enabled cues begin at 0.320, 13.340, and 26.340. However, the first two cues end exactly at the next cue start (13.340 and 26.340), so the original silent gaps still disappear from the subtitle timeline. I am therefore not claiming identical segment boundaries across models.

Minimal input construction from the repository root:

```bash
ffmpeg -y -f lavfi -i anullsrc=r=16000:cl=mono -t 2 \
  -c:a pcm_s16le /tmp/silence-2s.wav

ffmpeg -y \
  -i samples/jfk.wav -i /tmp/silence-2s.wav \
  -i samples/jfk.wav -i /tmp/silence-2s.wav \
  -i samples/jfk.wav \
  -filter_complex '[0:a][1:a][2:a][3:a][4:a]concat=n=5:v=0:a=1[out]' \
  -map '[out]' -ar 16000 -ac 1 -c:a pcm_s16le \
  /tmp/jfk-three-segments.wav
```

Commands used to inspect and transcribe it:

```bash
./build/bin/whisper-vad-speech-segments \
  -f /tmp/jfk-three-segments.wav \
  -vm /path/to/ggml-silero-v6.2.0.bin -t 8 -np

./build/bin/whisper-cli \
  -m /path/to/ggml-large-v3-turbo-q5_0.bin \
  -f /tmp/jfk-three-segments.wav -l en -t 8 \
  -osrt -of /tmp/jfk-vad-off

./build/bin/whisper-cli \
  -m /path/to/ggml-large-v3-turbo-q5_0.bin \
  -f /tmp/jfk-three-segments.wav -l en -t 8 \
  --vad -vm /path/to/ggml-silero-v6.2.0.bin \
  -osrt -of /tmp/jfk-vad-on
```

One possibly relevant implementation detail: CLI SRT output obtains segment times through `whisper_full_get_segment_t0/t1()`, whose VAD path uses `map_processed_to_original_time()` and linear interpolation between mapping points. PR #3910 added segment-aware remapping for token timestamp getters, including snapping token times out of removed silence, but the segment getters still use the older general mapping. This is only a possible explanation based on source inspection, not a confirmed root cause.

AI use disclosure: I used an AI assistant to help automate the comparison and organize this follow-up. I ran the reproduction locally, checked the generated SRT files, and reviewed the claims above.
