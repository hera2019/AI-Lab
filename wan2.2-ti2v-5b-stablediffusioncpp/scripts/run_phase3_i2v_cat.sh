#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${WAN22_MODEL_DIR:-$HOME/Documents/AI-Models/video/wan2.2-ti2v-5b}"
input_image="$project_dir/results/generated/phase-2-t2v/03-native-resolution-single-frame.png"
result_dir="$project_dir/results/generated/phase-3-i2v"
stem="01-cat-head-turn-33-frame-tae"
output_file="$result_dir/$stem.webm"
log_file="$result_dir/$stem.log"
prompt_file="$result_dir/$stem-prompt.txt"

prompt="The same fluffy cat slowly turns its head toward the camera and blinks once. Subtle natural breathing. Keep the cat's identity, fur pattern, body pose, white surface, orange background, framing, and lighting unchanged. Locked camera, realistic gentle motion."
negative_prompt="camera movement, scene change, background change, changing identity, changing fur pattern, deformed face, extra limbs, duplicated cat, sudden movement, flicker, blur, text, watermark"

required_files=(
    "$sd_cli"
    "$model_dir/diffusion/Wan2.2-TI2V-5B-Q4_K_M.gguf"
    "$model_dir/text-encoder/umt5-xxl-encoder-Q5_K_M.gguf"
    "$model_dir/tae/taew2_2.safetensors"
    "$input_image"
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
    printf 'Input image:\n%s\n\n' "results/generated/phase-2-t2v/03-native-resolution-single-frame.png"
    printf 'Prompt:\n%s\n\n' "$prompt"
    printf 'Negative prompt:\n%s\n\n' "$negative_prompt"
    printf '%s\n' 'Parameters: 832x480, 33 frames, 24 fps, 20 steps, CFG 6.0, Euler, flow shift 3.0, seed 260906, TAEHV encoder/decoder'
} >"$prompt_file"

/usr/bin/time -l "$sd_cli" \
    --mode vid_gen \
    --diffusion-model "$model_dir/diffusion/Wan2.2-TI2V-5B-Q4_K_M.gguf" \
    --t5xxl "$model_dir/text-encoder/umt5-xxl-encoder-Q5_K_M.gguf" \
    --tae "$model_dir/tae/taew2_2.safetensors" \
    --init-img "$input_image" \
    --prompt "$prompt" \
    --negative-prompt "$negative_prompt" \
    --width 832 \
    --height 480 \
    --video-frames 33 \
    --fps 24 \
    --steps 20 \
    --cfg-scale 6.0 \
    --sampling-method euler \
    --flow-shift 3.0 \
    --seed 260906 \
    --diffusion-fa \
    --offload-to-cpu \
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

echo "Phase 3 I2V cat test complete: results/generated/phase-3-i2v/"
