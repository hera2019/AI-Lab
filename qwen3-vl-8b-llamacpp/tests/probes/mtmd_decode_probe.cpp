#include "mtmd-helper.h"

#include <cstdint>
#include <cstdio>

int main(int argc, char ** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: mtmd_decode_probe IMAGE\n");
        return 2;
    }

    const mtmd_helper_init_opt opt = mtmd_helper_init_opt_default();
    mtmd_helper_bitmap_wrapper decoded =
        mtmd_helper_bitmap_init_from_file(nullptr, argv[1], false, opt);

    if (decoded.bitmap == nullptr) {
        std::fprintf(stderr, "decode failed: %s\n", argv[1]);
        return 1;
    }

    const uint32_t width = mtmd_bitmap_get_nx(decoded.bitmap);
    const uint32_t height = mtmd_bitmap_get_ny(decoded.bitmap);
    const size_t byte_count = mtmd_bitmap_get_n_bytes(decoded.bitmap);
    const unsigned char * rgb = mtmd_bitmap_get_data(decoded.bitmap);

    size_t pure_red = 0;
    size_t pure_green = 0;
    for (size_t offset = 0; offset + 2 < byte_count; offset += 3) {
        const unsigned char r = rgb[offset];
        const unsigned char g = rgb[offset + 1];
        const unsigned char b = rgb[offset + 2];
        pure_red += r == 255 && g == 0 && b == 0;
        pure_green += r == 0 && g == 255 && b == 0;
    }

    std::printf("file=%s\n", argv[1]);
    std::printf("decoded=%ux%u channels=3 bytes=%zu\n", width, height, byte_count);
    std::printf("first_rgb=%u,%u,%u\n", rgb[0], rgb[1], rgb[2]);
    std::printf("pure_red_pixels=%zu\n", pure_red);
    std::printf("pure_green_pixels=%zu\n", pure_green);

    mtmd_bitmap_free(decoded.bitmap);
    if (decoded.video_ctx != nullptr) {
        mtmd_helper_video_free(decoded.video_ctx);
    }
    return 0;
}
