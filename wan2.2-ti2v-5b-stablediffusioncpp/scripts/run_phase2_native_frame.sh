#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${WAN22_MODEL_DIR:-$HOME/Documents/AI-Models/video/wan2.2-ti2v-5b}"
result_dir="$project_dir/results/generated/phase-2-t2v"
stem="03-native-resolution-single-frame"
output_file="$result_dir/$stem.png"
log_file="$result_dir/$stem.log"
prompt_file="$result_dir/$stem-prompt.txt"

prompt="A lovely cat sitting calmly, centered in frame, clear full body, natural daylight, realistic photograph."
negative_prompt="oversaturated, overexposed, static video, blurry details, subtitles, painting, gray image, worst quality, low quality, JPEG artifacts, ugly, deformed body, duplicated animal, distorted shape, text, watermark"

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
    printf '%s\n' 'Parameters: 832x480, 1 frame, 20 steps, CFG 6.0, Euler, flow shift 3.0, seed 260905'
} >"$prompt_file"

/usr/bin/time -l "$sd_cli" \
    --mode vid_gen \
    --diffusion-model "$model_dir/diffusion/Wan2.2-TI2V-5B-Q4_K_M.gguf" \
    --t5xxl "$model_dir/text-encoder/umt5-xxl-encoder-Q5_K_M.gguf" \
    --vae "$model_dir/vae/wan2.2_vae.safetensors" \
    --prompt "$prompt" \
    --negative-prompt "$negative_prompt" \
    --width 832 \
    --height 480 \
    --video-frames 1 \
    --fps 24 \
    --steps 20 \
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
    echo "No valid image was created" >&2
    exit 4
fi

sips -g pixelWidth -g pixelHeight -g format "$output_file" \
    >"$result_dir/$stem-image-info.txt"

echo "Native-resolution single-frame test complete: results/generated/phase-2-t2v/"
