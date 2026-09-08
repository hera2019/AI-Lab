#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sd_cli="${SD_CLI:-$project_dir/worktrees/stable-diffusion.cpp/build-release-metal/bin/sd-cli}"
model_dir="${FLUX2_MODEL_DIR:-$HOME/Documents/AI-Models/stable-diffusion/flux2-klein-4b}"
result_dir="$project_dir/results/generated/phase-3-assisted-composite"
init_image="$result_dir/02-layer-composite-warm.png"
mask_image="$result_dir/refinement-mask.png"
mode="${1:-standard}"

case "$mode" in
    standard)
        object_reference="$project_dir/results/generated/phase-2-instruction-isolation/02-color.png"
        output_file="$result_dir/03-flux-mask-refinement-raw.png"
        log_file="$result_dir/03-flux-mask-refinement-raw.log"
        prompt_file="$result_dir/03-flux-mask-refinement-prompt.txt"
        seed="260913"
        strength="0.75"
        prompt="Refine only the single green ceramic mug already positioned on the wooden serving counter, immediately to the right of the small blue ceramic cat. Keep the mug in exactly the same position, size, and orientation. Preserve its green ceramic material and right-side handle, using the center green mug in the reference image as the product reference. Integrate it naturally into the ramen shop with warm amber indoor lighting, realistic contact shadow, subtle counter reflection, clean edges, and correct perspective. Do not move, resize, duplicate, or remove the mug. Do not change the blue cat, counter, shop, people, sign, lanterns, bicycle, rainy street, composition, or any area outside the local masked region. Add no object, animal, person, text, logo, symbol, or decoration."
        ;;
    conservative)
        object_reference="$result_dir/green-mug-cutout.png"
        output_file="$result_dir/04-flux-mask-refinement-conservative-raw.png"
        log_file="$result_dir/04-flux-mask-refinement-conservative-raw.log"
        prompt_file="$result_dir/04-flux-mask-refinement-conservative-prompt.txt"
        seed="260914"
        strength="0.35"
        prompt="Preserve the one green ceramic mug already present on the wooden serving counter to the right of the blue ceramic cat. The separate reference image shows this exact mug. Keep its exact position, size, silhouette, right-side handle, and green color. Make only subtle local improvements to the mug edge, warm amber lighting, contact shadow, and counter reflection so it looks naturally photographed in the existing shop. Do not erase, replace, move, resize, or duplicate the mug. Do not create any person, animal, cup, furniture, text, or decoration. Do not change anything outside the masked area."
        ;;
    scale-corrected)
        corrected_dir="$result_dir/scale-corrected"
        init_image="$corrected_dir/02-layer-composite-warm.png"
        mask_image="$corrected_dir/refinement-mask.png"
        object_reference="$corrected_dir/green-mug-cutout.png"
        output_file="$corrected_dir/03-flux-mask-refinement-raw.png"
        log_file="$corrected_dir/03-flux-mask-refinement-raw.log"
        prompt_file="$corrected_dir/03-flux-mask-refinement-prompt.txt"
        seed="260915"
        strength="0.35"
        prompt="Preserve the one realistically small green ceramic mug already positioned on the wooden serving counter to the right of the blue ceramic cat. The separate reference image shows this exact mug. Keep its current exact small size, position, silhouette, right-side handle, and green color. A normal drinking mug should remain smaller than the nearby blue cat ornament and appropriately scaled for the counter. Make only subtle local improvements to its edge, warm amber lighting, contact shadow, and counter reflection. Do not enlarge, move, erase, replace, or duplicate the mug. Do not create any person, animal, cup, furniture, text, or decoration. Do not change anything outside the masked area."
        ;;
    *)
        echo "Usage: $0 [standard|conservative|scale-corrected]" >&2
        exit 2
        ;;
esac

required_files=(
    "$sd_cli"
    "$init_image"
    "$mask_image"
    "$object_reference"
    "$model_dir/diffusion/flux-2-klein-4b-Q4_0.gguf"
    "$model_dir/text-encoder/Qwen3-4B-Q4_K_M.gguf"
    "$model_dir/vae/full_encoder_small_decoder.safetensors"
)

for path in "${required_files[@]}"; do
    if [[ ! -f "$path" ]]; then
        echo "Required file not found: $path" >&2
        exit 2
    fi
done

if [[ -e "$output_file" ]]; then
    echo "Output already exists; refusing to overwrite: $output_file" >&2
    exit 3
fi

printf '%s\n' "$prompt" >"$prompt_file"

echo "Refining only the masked mug region (mode $mode, seed $seed, 1024x1024, 4 steps, strength $strength)"

/usr/bin/time -l "$sd_cli" \
    --diffusion-model "$model_dir/diffusion/flux-2-klein-4b-Q4_0.gguf" \
    --llm "$model_dir/text-encoder/Qwen3-4B-Q4_K_M.gguf" \
    --vae "$model_dir/vae/full_encoder_small_decoder.safetensors" \
    --init-img "$init_image" \
    --mask "$mask_image" \
    --ref-image "$object_reference" \
    --ref-image-args "preset=flux2" \
    --prompt "$prompt" \
    --width 1024 \
    --height 1024 \
    --steps 4 \
    --strength "$strength" \
    --cfg-scale 1.0 \
    --sampling-method euler \
    --seed "$seed" \
    --diffusion-fa \
    --offload-to-cpu \
    --verbose \
    --output "$output_file" 2>&1 | tee "$log_file"

if [[ ! -s "$output_file" ]]; then
    echo "No valid output image was created" >&2
    exit 4
fi

echo "Masked refinement complete: ${output_file#"$project_dir/"}"
