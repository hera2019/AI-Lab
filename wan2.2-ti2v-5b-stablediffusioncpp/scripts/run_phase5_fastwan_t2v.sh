#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${WAN22_MODEL_DIR:-$HOME/Documents/AI-Models/video/wan2.2-ti2v-5b}"
result_dir="$project_dir/results/generated/phase-5-fastwan"
stem="01-fastwan-cat-t2v-3step"
output_file="$result_dir/$stem.webm"
log_file="$result_dir/$stem.log"
prompt_file="$result_dir/$stem-prompt.txt"

prompt="A lovely fluffy cat sitting calmly on a white surface, centered in frame, natural daylight, realistic video. The cat slowly turns its head slightly to the left and blinks once. The body and background remain still. Locked camera, consistent anatomy, consistent fur pattern."
negative_prompt="oversaturated, overexposed, blurry details, subtitles, painting, worst quality, low quality, deformed body, extra limbs, duplicated animal, changing fur pattern, distorted face, camera movement, text, watermark"

required_files=(
    "$sd_cli"
    "$model_dir/diffusion-fastwan/FastWan2.2-TI2V-5B-q8_0.gguf"
    "$model_dir/text-encoder/umt5-xxl-encoder-Q5_K_M.gguf"
    "$model_dir/tae/taew2_2.safetensors"
)

for path in "${required_files[@]}"; do
    if [[ ! -f "$path" ]]; then
        echo "Required file not found: $path" >&2
        exit 2
    fi
done

mkdir -p "$result_dir"
if [[ -e "$output_file" ]]; then
    echo "Output already exists; refusing to overwrite: $output_file" >&2
    exit 3
fi

{
    printf 'Prompt:\n%s\n\n' "$prompt"
    printf 'Negative prompt:\n%s\n\n' "$negative_prompt"
    printf '%s\n' 'Parameters: 832x480, 33 frames, 24 fps, 3 steps, CFG 1.0, Euler, LCM scheduler, flow shift 3.0, seed 260905, FastWan Q8_0, TAEHV decoder'
} >"$prompt_file"

/usr/bin/time -l "$sd_cli" \
    --mode vid_gen \
    --diffusion-model "$model_dir/diffusion-fastwan/FastWan2.2-TI2V-5B-q8_0.gguf" \
    --t5xxl "$model_dir/text-encoder/umt5-xxl-encoder-Q5_K_M.gguf" \
    --tae "$model_dir/tae/taew2_2.safetensors" \
    --prompt "$prompt" \
    --negative-prompt "$negative_prompt" \
    --width 832 \
    --height 480 \
    --video-frames 33 \
    --fps 24 \
    --steps 3 \
    --cfg-scale 1.0 \
    --sampling-method euler \
    --scheduler lcm \
    --flow-shift 3.0 \
    --seed 260905 \
    --diffusion-fa \
    --offload-to-cpu \
    --vae-conv-direct \
    --verbose \
    --output "$output_file" 2>&1 | tee "$log_file"

if [[ ! -s "$output_file" ]]; then
    echo "No valid video was created" >&2
    exit 4
fi

ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames,duration \
    -show_entries format=duration,size -of json "$output_file" \
    >"$result_dir/$stem-ffprobe.json"

ffmpeg -v error -i "$output_file" -f null -

ffmpeg -hide_banner -loglevel error -i "$output_file" \
    -vf "select='eq(n,0)+eq(n,16)+eq(n,31)',tile=3x1" \
    -frames:v 1 "$result_dir/$stem-contact-sheet.png"

ffmpeg -hide_banner -loglevel error -i "$output_file" -an \
    -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
    "$result_dir/$stem.mp4"

ffmpeg -hide_banner -loglevel error -i "$output_file" -an \
    -vf "setpts=2.0*PTS" -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
    "$result_dir/$stem-slow-2x.mp4"

echo "FastWan 3-step T2V test complete: results/generated/phase-5-fastwan/"
