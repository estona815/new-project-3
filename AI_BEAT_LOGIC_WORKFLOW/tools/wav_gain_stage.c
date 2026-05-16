#include "wav_common.h"

static int parse_args(int argc, char **argv, const char **input, const char **output, double *target_peak_db) {
    if (argc != 5 || strcmp(argv[3], "--target-peak-db") != 0) {
        fprintf(stderr, "usage: %s input.wav output.wav --target-peak-db -3.0\n", argv[0]);
        return 0;
    }
    *input = argv[1];
    *output = argv[2];
    char *end = NULL;
    *target_peak_db = strtod(argv[4], &end);
    if (!end || *end != '\0') {
        fprintf(stderr, "invalid target peak value: %s\n", argv[4]);
        return 0;
    }
    return 1;
}

int main(int argc, char **argv) {
    const char *input = NULL;
    const char *output = NULL;
    double target_peak_db = -3.0;
    if (!parse_args(argc, argv, &input, &output, &target_peak_db)) {
        return 2;
    }

    char error[512];
    WavData wav;
    if (!wav_read(input, &wav, error, sizeof(error))) {
        fprintf(stderr, "wav_gain_stage: %s\n", error);
        return 1;
    }

    size_t sample_count = (size_t)wav.frame_count * wav.channels;
    double peak = 0.0;
    for (size_t i = 0; i < sample_count; i++) {
        double absolute = fabs((double)wav.samples[i]);
        if (absolute > peak) {
            peak = absolute;
        }
    }

    if (peak <= 0.0) {
        fprintf(stderr, "wav_gain_stage: input is silent; refusing to normalize peak\n");
        wav_free(&wav);
        return 1;
    }

    double target_linear = pow(10.0, target_peak_db / 20.0);
    if (target_linear <= 0.0 || target_linear > 1.0) {
        fprintf(stderr, "wav_gain_stage: target peak must be <= 0 dBFS\n");
        wav_free(&wav);
        return 1;
    }

    double gain = target_linear / peak;
    float *processed = (float *)calloc(sample_count, sizeof(float));
    if (!processed) {
        fprintf(stderr, "wav_gain_stage: out of memory\n");
        wav_free(&wav);
        return 1;
    }
    for (size_t i = 0; i < sample_count; i++) {
        processed[i] = clamp_sample((float)((double)wav.samples[i] * gain));
    }

    int ok = wav_write_float32(output, &wav, processed, wav.frame_count, error, sizeof(error));
    free(processed);
    wav_free(&wav);
    if (!ok) {
        fprintf(stderr, "wav_gain_stage: %s\n", error);
        return 1;
    }
    return 0;
}

