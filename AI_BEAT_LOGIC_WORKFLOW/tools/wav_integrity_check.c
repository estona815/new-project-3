#include "wav_common.h"

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s input.wav\n", argv[0]);
        return 2;
    }

    char error[512];
    WavData wav;
    if (!wav_read(argv[1], &wav, error, sizeof(error))) {
        printf("{\n");
        printf("  \"path\": \"%s\",\n", argv[1]);
        printf("  \"pass\": false,\n");
        printf("  \"error\": \"%s\"\n", error);
        printf("}\n");
        fprintf(stderr, "wav_integrity_check: %s\n", error);
        return 1;
    }

    int size_ok = wav_file_size_matches_data(argv[1], &wav);
    printf("{\n");
    printf("  \"path\": \"%s\",\n", argv[1]);
    printf("  \"pass\": %s,\n", size_ok ? "true" : "false");
    printf("  \"sample_rate\": %u,\n", wav.sample_rate);
    printf("  \"channels\": %u,\n", wav.channels);
    printf("  \"bits_per_sample\": %u,\n", wav.bits_per_sample);
    printf("  \"data_size\": %u,\n", wav.data_size);
    printf("  \"frame_count\": %u\n", wav.frame_count);
    printf("}\n");

    wav_free(&wav);
    return size_ok ? 0 : 1;
}

