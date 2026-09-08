#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${WAN22_MODEL_DIR:-$HOME/Documents/AI-Models/video/wan2.2-ti2v-5b}"
result_dir="$project_dir/results/generated/phase-2-t2v"
stem="01-red-sailboat-12-step"
output_file="$result_dir/$stem.webm"
log_file="$result_dir/$stem.log"
prompt_file="$result_dir/$stem-prompt.txt"

prompt="A cinematic close-up video of a small red toy sailboat floating gently in a clear glass bowl of water on a wooden table. The boat rocks slowly from side to side while soft sunlight reflections move across the water. The bowl and table remain stationary. Locked camera, realistic motion, consistent shape, no text."
negative_prompt="blurry, low quality, flicker, jitter, sudden movement, warped object, duplicated boat, changing shape, camera movement, text, watermark"

required_files=(
    "$sd_cli"
    "$model_dir/diffusion/Wan2.2-TI2V-5B-Q4_K_M.gguf"
    "$model_dir/text-encoder/umt5-xxl-encoder-Q5_K_M.gguf"
    "$model_dir/vae/wan2.2_vae.safetensors"
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
    printf '%s\n' 'Parameters: 416x256, 17 frames, 24 fps, 12 steps, CFG 6.0, Euler, flow shift 3.0, seed 260905'
} >"$prompt_file"

/usr/bin/time -l "$sd_cli" \
    --mode vid_gen \
    --diffusion-model "$model_dir/diffusion/Wan2.2-TI2V-5B-Q4_K_M.gguf" \
    --t5xxl "$model_dir/text-encoder/umt5-xxl-encoder-Q5_K_M.gguf" \
    --vae "$model_dir/vae/wan2.2_vae.safetensors" \
    --prompt "$prompt" \
    --negative-prompt "$negative_prompt" \
    --width 416 \
    --height 256 \
    --video-frames 17 \
    --fps 24 \
    --steps 12 \
    --cfg-scale 6.0 \
    --sampling-method euler \
    --flow-shift 3.0 \
    --seed 260905 \
    --diffusion-fa \
    --offload-to-cpu \
    --vae-tiling \
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
    -vf "select='eq(n,0)+eq(n,8)+eq(n,15)',tile=3x1" \
    -frames:v 1 "$result_dir/$stem-contact-sheet.png"

echo "Phase 2 quality baseline complete: results/generated/phase-2-t2v/"
