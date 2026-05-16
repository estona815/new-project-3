#include "wav_common.h"

static int parse_double_arg(const char *text, double *value) {
    char *end = NULL;
    *value = strtod(text, &end);
    return end && *end == '\0';
}

static int parse_args(int argc, char **argv, const char **input, const char **output, double *start, double *end, double *fade_in, double *fade_out) {
    if (argc != 11) {
        fprintf(stderr, "usage: %s input.wav output.wav --start 5.0 --end 125.0 --fade-in 0.02 --fade-out 1.5\n", argv[0]);
        return 0;
    }
    *input = argv[1];
    *output = argv[2];
    for (int i = 3; i < argc; i += 2) {
        if (i + 1 >= argc) {
            return 0;
        }
        if (strcmp(argv[i], "--start") == 0) {
            if (!parse_double_arg(argv[i + 1], start)) return 0;
        } else if (strcmp(argv[i], "--end") == 0) {
            if (!parse_double_arg(argv[i + 1], end)) return 0;
        } else if (strcmp(argv[i], "--fade-in") == 0) {
            if (!parse_double_arg(argv[i + 1], fade_in)) return 0;
        } else if (strcmp(argv[i], "--fade-out") == 0) {
            if (!parse_double_arg(argv[i + 1], fade_out)) return 0;
        } else {
            fprintf(stderr, "unknown option: %s\n", argv[i]);
            return 0;
        }
    }
    return 1;
}

int main(int argc, char **argv) {
    const char *input = NULL;
    const char *output = NULL;
    double start_seconds = 0.0;
    double end_seconds = 0.0;
    double fade_in_seconds = 0.0;
    double fade_out_seconds = 0.0;
    if (!parse_args(argc, argv, &input, &output, &start_seconds, &end_seconds, &fade_in_seconds, &fade_out_seconds)) {
        return 2;
    }
    if (start_seconds < 0.0 || end_seconds <= start_seconds || fade_in_seconds < 0.0 || fade_out_seconds < 0.0) {
        fprintf(stderr, "wav_trim_fade: invalid timing arguments\n");
        return 1;
    }

    char error[512];
    WavData wav;
    if (!wav_read(input, &wav, error, sizeof(error))) {
        fprintf(stderr, "wav_trim_fade: %s\n", error);
        return 1;
    }

    uint32_t start_frame = (uint32_t)floor(start_seconds * wav.sample_rate);
    uint32_t end_frame = (uint32_t)ceil(end_seconds * wav.sample_rate);
    if (start_frame >= wav.frame_count) {
        fprintf(stderr, "wav_trim_fade: start is beyond input duration\n");
        wav_free(&wav);
        return 1;
    }
    if (end_frame > wav.frame_count) {
        end_frame = wav.frame_count;
    }
    if (end_frame <= start_frame) {
        fprintf(stderr, "wav_trim_fade: trim range is empty\n");
        wav_free(&wav);
        return 1;
    }

    uint32_t output_frames = end_frame - start_frame;
    size_t output_samples = (size_t)output_frames * wav.channels;
    float *processed = (float *)calloc(output_samples, sizeof(float));
    if (!processed) {
        fprintf(stderr, "wav_trim_fade: out of memory\n");
        wav_free(&wav);
        return 1;
    }

    uint32_t fade_in_frames = (uint32_t)(fade_in_seconds * wav.sample_rate);
    uint32_t fade_out_frames = (uint32_t)(fade_out_seconds * wav.sample_rate);
    for (uint32_t frame = 0; frame < output_frames; frame++) {
        double gain = 1.0;
        if (fade_in_frames > 0 && frame < fade_in_frames) {
            gain *= (double)frame / (double)fade_in_frames;
        }
        if (fade_out_frames > 0 && frame >= output_frames - (fade_out_frames < output_frames ? fade_out_frames : output_frames)) {
            uint32_t remaining = output_frames - frame;
            gain *= (double)remaining / (double)(fade_out_frames < output_frames ? fade_out_frames : output_frames);
        }
        for (uint16_t ch = 0; ch < wav.channels; ch++) {
            size_t src_index = (size_t)(start_frame + frame) * wav.channels + ch;
            size_t dst_index = (size_t)frame * wav.channels + ch;
            processed[dst_index] = (float)((double)wav.samples[src_index] * gain);
        }
    }

    int ok = wav_write_float32(output, &wav, processed, output_frames, error, sizeof(error));
    free(processed);
    wav_free(&wav);
    if (!ok) {
        fprintf(stderr, "wav_trim_fade: %s\n", error);
        return 1;
    }
    return 0;
}

