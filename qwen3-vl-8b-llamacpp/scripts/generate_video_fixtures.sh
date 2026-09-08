#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_dir="$project_dir/tests/fixtures"
video_dir="$fixture_dir/video"
vfr_list=""

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
    echo "ffmpeg and ffprobe are required" >&2
    exit 1
fi

mkdir -p "$video_dir"

cleanup() {
    if [[ -n "$vfr_list" ]]; then
        rm -f -- "$vfr_list"
    fi
}
trap cleanup EXIT

make_video() {
    local output_file="$1"
    local first_image="$2"
    local second_image="$3"
    local third_image="$4"

    ffmpeg -hide_banner -loglevel error -y \
        -loop 1 -t 2 -i "$first_image" \
        -loop 1 -t 2 -i "$second_image" \
        -loop 1 -t 2 -i "$third_image" \
        -filter_complex \
        "[0:v]fps=6,format=yuv420p,setsar=1[v0];[1:v]fps=6,format=yuv420p,setsar=1[v1];[2:v]fps=6,format=yuv420p,setsar=1[v2];[v0][v1][v2]concat=n=3:v=1:a=0[v]" \
        -map "[v]" \
        -c:v libx264 \
        -preset veryfast \
        -crf 18 \
        -movflags +faststart \
        "$output_file"
}

image_a="$fixture_dir/multi/14-multi-a-red-circle.png"
image_b="$fixture_dir/multi/15-multi-b-blue-square.png"
image_c="$fixture_dir/multi/16-multi-c-green-triangle.png"

make_video "$video_dir/20-video-abc.mp4" "$image_a" "$image_b" "$image_c"
make_video "$video_dir/21-video-cba-猫-東京-🧪.mp4" "$image_c" "$image_b" "$image_a"

ffmpeg -hide_banner -loglevel error -y \
    -loop 1 -t 0.2 -i "$image_a" \
    -vf "fps=10,format=yuv420p,setsar=1" \
    -c:v libx264 \
    -preset veryfast \
    -crf 18 \
    -movflags +faststart \
    "$video_dir/22-video-a-very-short.mp4"

ffmpeg -hide_banner -loglevel error -y \
    -i "$video_dir/20-video-abc.mp4" \
    -map 0:v:0 \
    -c copy \
    "$video_dir/23-video-abc-moov-tail.mp4"

vfr_list="$(mktemp -t qwen3-vl-video-vfr.XXXXXX)"
printf "file '%s'\nduration 1.0\nfile '%s'\nduration 3.0\nfile '%s'\nduration 2.0\nfile '%s'\n" \
    "$image_a" "$image_b" "$image_c" "$image_c" >"$vfr_list"
ffmpeg -hide_banner -loglevel error -y \
    -f concat \
    -safe 0 \
    -i "$vfr_list" \
    -vf "format=yuv420p,setsar=1" \
    -fps_mode vfr \
    -c:v libx264 \
    -preset veryfast \
    -crf 18 \
    -movflags +faststart \
    "$video_dir/24-video-vfr-abc.mp4"

printf 'this is not an MP4 file\n' >"$video_dir/25-not-a-video.mp4"

for video_file in "$video_dir"/*.mp4; do
    echo
    echo "===== ${video_file#$project_dir/} ====="
    ffprobe -v error \
        -count_frames \
        -show_entries format=duration,size:stream=codec_name,codec_type,width,height,avg_frame_rate,nb_read_frames \
        -of default=noprint_wrappers=1 \
        "$video_file" || true
done
