#include "wav_common.h"

#define SILENCE_THRESHOLD 0.001
#define SILENCE_MIN_SECONDS 0.5
#define MAX_SILENCE_REGIONS 128

typedef struct {
    double start;
    double end;
} Region;

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s input.wav\n", argv[0]);
        return 2;
    }

    char error[512];
    WavData wav;
    if (!wav_read(argv[1], &wav, error, sizeof(error))) {
        fprintf(stderr, "wav_analyzer: %s\n", error);
        return 1;
    }

    size_t sample_count = (size_t)wav.frame_count * wav.channels;
    double peak = 0.0;
    double sum_sq = 0.0;
    uint64_t clipped_count = 0;
    for (size_t i = 0; i < sample_count; i++) {
        double absolute = fabs((double)wav.samples[i]);
        if (absolute > peak) {
            peak = absolute;
        }
        sum_sq += absolute * absolute;
        if (absolute >= 0.999969) {
            clipped_count++;
        }
    }

    double rms = sample_count > 0 ? sqrt(sum_sq / (double)sample_count) : 0.0;
    double duration = wav.sample_rate > 0 ? (double)wav.frame_count / (double)wav.sample_rate : 0.0;
    uint32_t min_silence_frames = (uint32_t)(SILENCE_MIN_SECONDS * wav.sample_rate);
    Region regions[MAX_SILENCE_REGIONS];
    int region_count = 0;
    uint32_t silence_start = 0;
    int in_silence = 0;

    for (uint32_t frame = 0; frame < wav.frame_count; frame++) {
        double frame_peak = 0.0;
        for (uint16_t ch = 0; ch < wav.channels; ch++) {
            double absolute = fabs((double)wav.samples[(size_t)frame * wav.channels + ch]);
            if (absolute > frame_peak) {
                frame_peak = absolute;
            }
        }
        if (frame_peak < SILENCE_THRESHOLD) {
            if (!in_silence) {
                in_silence = 1;
                silence_start = frame;
            }
        } else if (in_silence) {
            uint32_t silence_len = frame - silence_start;
            if (silence_len >= min_silence_frames && region_count < MAX_SILENCE_REGIONS) {
                regions[region_count].start = (double)silence_start / wav.sample_rate;
                regions[region_count].end = (double)frame / wav.sample_rate;
                region_count++;
            }
            in_silence = 0;
        }
    }
    if (in_silence) {
        uint32_t silence_len = wav.frame_count - silence_start;
        if (silence_len >= min_silence_frames && region_count < MAX_SILENCE_REGIONS) {
            regions[region_count].start = (double)silence_start / wav.sample_rate;
            regions[region_count].end = (double)wav.frame_count / wav.sample_rate;
            region_count++;
        }
    }

    printf("{\n");
    printf("  \"path\": \"%s\",\n", argv[1]);
    printf("  \"sample_rate\": %u,\n", wav.sample_rate);
    printf("  \"channels\": %u,\n", wav.channels);
    printf("  \"bits_per_sample\": %u,\n", wav.bits_per_sample);
    printf("  \"duration_seconds\": %.6f,\n", duration);
    printf("  \"peak_dbfs\": %.6f,\n", linear_to_db(peak));
    printf("  \"rms_dbfs\": %.6f,\n", linear_to_db(rms));
    printf("  \"possible_clipping\": %s,\n", clipped_count > 0 ? "true" : "false");
    printf("  \"clipped_sample_count\": %llu,\n", (unsigned long long)clipped_count);
    printf("  \"silence_regions\": [\n");
    for (int i = 0; i < region_count; i++) {
        printf("    {\"start\": %.6f, \"end\": %.6f}%s\n", regions[i].start, regions[i].end, i == region_count - 1 ? "" : ",");
    }
    printf("  ]\n");
    printf("}\n");

    wav_free(&wav);
    return 0;
}

