#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${WAN22_MODEL_DIR:-$HOME/Documents/AI-Models/video/wan2.2-ti2v-5b}"
input_image="$project_dir/results/generated/phase-2-t2v/03-native-resolution-single-frame.png"
result_dir="$project_dir/results/generated/phase-5-fastwan"
stem="05-fastwan-cat-i2v-blink-65frame"
output_file="$result_dir/$stem.webm"
log_file="$result_dir/$stem.log"
prompt_file="$result_dir/$stem-prompt.txt"

prompt="The same fluffy cat remains perfectly still and looks directly at the camera. Near the middle of the shot, it performs one slow and clearly visible blink: both eyes close completely, remain closed briefly, and then fully reopen. Keep the head, body, paws, tail, identity, face, fur pattern, background, framing, and lighting unchanged. Locked camera, no zoom."
negative_prompt="head turn, head movement, body movement, paw movement, tail movement, camera movement, zoom, scene change, background change, changing identity, changing fur pattern, deformed face, asymmetric eyes, only one eye closed, extra limbs, sudden motion, flicker, blur, text, watermark"

required_files=(
    "$sd_cli"
    "$model_dir/diffusion-fastwan/FastWan2.2-TI2V-5B-q8_0.gguf"
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
    printf 'Input image:\n%s\n\n' 'results/generated/phase-2-t2v/03-native-resolution-single-frame.png'
    printf 'Prompt:\n%s\n\n' "$prompt"
    printf 'Negative prompt:\n%s\n\n' "$negative_prompt"
    printf '%s\n' 'Parameters: 832x480, 65 frames, 24 fps, 3 steps, CFG 1.0, strength 0.75, Euler, LCM scheduler, flow shift 3.0, seed 260909, FastWan Q8_0, TAEHV, default VAE convolution'
} >"$prompt_file"

/usr/bin/time -l "$sd_cli" \
    --mode vid_gen \
    --diffusion-model "$model_dir/diffusion-fastwan/FastWan2.2-TI2V-5B-q8_0.gguf" \
    --t5xxl "$model_dir/text-encoder/umt5-xxl-encoder-Q5_K_M.gguf" \
    --tae "$model_dir/tae/taew2_2.safetensors" \
    --init-img "$input_image" \
    --prompt "$prompt" \
    --negative-prompt "$negative_prompt" \
    --width 832 \
    --height 480 \
    --video-frames 65 \
    --fps 24 \
    --steps 3 \
    --cfg-scale 1.0 \
    --strength 0.75 \
    --sampling-method euler \
    --scheduler lcm \
    --flow-shift 3.0 \
    --seed 260909 \
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
    -vf "select='eq(n,0)+eq(n,16)+eq(n,28)+eq(n,32)+eq(n,36)+eq(n,48)+eq(n,63)',tile=7x1" \
    -frames:v 1 "$result_dir/$stem-contact-sheet.png"

ffmpeg -hide_banner -loglevel error -i "$output_file" -an \
    -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
    "$result_dir/$stem.mp4"

ffmpeg -hide_banner -loglevel error -i "$output_file" -an \
    -vf "setpts=2.0*PTS" -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
    "$result_dir/$stem-slow-2x.mp4"

echo "FastWan 65-frame blink-only I2V test complete: results/generated/phase-5-fastwan/"
