#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${WAN22_MODEL_DIR:-$HOME/Documents/AI-Models/video/wan2.2-ti2v-5b}"
input_image="$project_dir/results/generated/phase-2-t2v/03-native-resolution-single-frame.png"
result_dir="$project_dir/results/generated/phase-5-fastwan"
stem="04-fastwan-cat-i2v-head-turn-65frame"
output_file="$result_dir/$stem.webm"
log_file="$result_dir/$stem.log"
prompt_file="$result_dir/$stem-prompt.txt"

prompt="The same fluffy cat remains seated on the white surface in front of the orange background. Over the entire shot, it slowly and clearly turns its head from facing the camera to look about 45 degrees toward the viewer's right. The head rotates in place and never moves closer to the camera. Its eyes follow the turn and it blinks once near the end. Keep both front paws planted, and keep the cat's body, tail, identity, face, fur pattern, size, background, framing, and lighting unchanged. Locked camera, no zoom, continuous realistic motion."
negative_prompt="camera movement, zoom, head moving toward camera, enlarged head, distorted face, changing identity, changing fur pattern, changing eye color, paw movement, body movement, extra limbs, duplicated cat, sudden motion, flicker, blur, scene change, background change, text, watermark"

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
    printf '%s\n' 'Parameters: 832x480, 65 frames, 24 fps, 3 steps, CFG 1.0, strength 0.75, Euler, LCM scheduler, flow shift 3.0, seed 260908, FastWan Q8_0, TAEHV, default VAE convolution'
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
    --seed 260908 \
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
    -vf "select='eq(n,0)+eq(n,16)+eq(n,32)+eq(n,48)+eq(n,63)',tile=5x1" \
    -frames:v 1 "$result_dir/$stem-contact-sheet.png"

ffmpeg -hide_banner -loglevel error -i "$output_file" -an \
    -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
    "$result_dir/$stem.mp4"

ffmpeg -hide_banner -loglevel error -i "$output_file" -an \
    -vf "setpts=2.0*PTS" -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
    "$result_dir/$stem-slow-2x.mp4"

echo "FastWan 65-frame head-turn I2V test complete: results/generated/phase-5-fastwan/"
