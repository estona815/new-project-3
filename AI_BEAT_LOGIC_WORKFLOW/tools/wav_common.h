#ifndef AI_BEAT_WAV_COMMON_H
#define AI_BEAT_WAV_COMMON_H

#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(__GNUC__) || defined(__clang__)
#define WAV_UNUSED __attribute__((unused))
#else
#define WAV_UNUSED
#endif

typedef struct {
    uint16_t audio_format;
    uint16_t channels;
    uint32_t sample_rate;
    uint16_t bits_per_sample;
    uint32_t data_size;
    uint32_t frame_count;
    float *samples;
} WavData;

static uint16_t read_le16(const unsigned char *b) {
    return (uint16_t)(b[0] | (b[1] << 8));
}

static uint32_t read_le32(const unsigned char *b) {
    return (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
}

static void write_le16(FILE *f, uint16_t value) {
    unsigned char b[2];
    b[0] = (unsigned char)(value & 0xff);
    b[1] = (unsigned char)((value >> 8) & 0xff);
    fwrite(b, 1, 2, f);
}

static void write_le32(FILE *f, uint32_t value) {
    unsigned char b[4];
    b[0] = (unsigned char)(value & 0xff);
    b[1] = (unsigned char)((value >> 8) & 0xff);
    b[2] = (unsigned char)((value >> 16) & 0xff);
    b[3] = (unsigned char)((value >> 24) & 0xff);
    fwrite(b, 1, 4, f);
}

static int read_exact(FILE *f, void *buffer, size_t size) {
    return fread(buffer, 1, size, f) == size;
}

static int skip_bytes(FILE *f, uint32_t size) {
    if (fseek(f, (long)size, SEEK_CUR) != 0) {
        return 0;
    }
    if (size % 2 == 1 && fseek(f, 1, SEEK_CUR) != 0) {
        return 0;
    }
    return 1;
}

static void wav_free(WavData *wav) {
    if (wav) {
        free(wav->samples);
        wav->samples = NULL;
    }
}

static float clamp_sample(float value) {
    if (value > 1.0f) {
        return 1.0f;
    }
    if (value < -1.0f) {
        return -1.0f;
    }
    return value;
}

static float pcm_to_float(const unsigned char *bytes, uint16_t bits_per_sample) {
    if (bits_per_sample == 16) {
        int16_t value = (int16_t)read_le16(bytes);
        return value < 0 ? (float)value / 32768.0f : (float)value / 32767.0f;
    }
    if (bits_per_sample == 24) {
        int32_t value = (int32_t)(bytes[0] | (bytes[1] << 8) | (bytes[2] << 16));
        if (value & 0x00800000) {
            value |= (int32_t)0xff000000;
        }
        return value < 0 ? (float)value / 8388608.0f : (float)value / 8388607.0f;
    }
    if (bits_per_sample == 32) {
        int32_t value = (int32_t)read_le32(bytes);
        return value < 0 ? (float)value / 2147483648.0f : (float)value / 2147483647.0f;
    }
    return 0.0f;
}

static float float32_to_float(const unsigned char *bytes) {
    uint32_t raw = read_le32(bytes);
    float value;
    memcpy(&value, &raw, sizeof(value));
    if (!isfinite(value)) {
        return 0.0f;
    }
    return clamp_sample(value);
}

static int wav_read(const char *path, WavData *wav, char *error, size_t error_size) {
    memset(wav, 0, sizeof(*wav));
    FILE *f = fopen(path, "rb");
    if (!f) {
        snprintf(error, error_size, "failed to open '%s': %s", path, strerror(errno));
        return 0;
    }

    unsigned char header[12];
    if (!read_exact(f, header, sizeof(header))) {
        snprintf(error, error_size, "file is too small to be a WAV file");
        fclose(f);
        return 0;
    }
    if (memcmp(header, "RIFF", 4) != 0 || memcmp(header + 8, "WAVE", 4) != 0) {
        snprintf(error, error_size, "invalid RIFF/WAVE header");
        fclose(f);
        return 0;
    }

    int have_fmt = 0;
    int have_data = 0;
    uint16_t block_align = 0;
    uint32_t data_offset = 0;

    while (!feof(f)) {
        unsigned char chunk_header[8];
        if (!read_exact(f, chunk_header, sizeof(chunk_header))) {
            break;
        }
        uint32_t chunk_size = read_le32(chunk_header + 4);
        long chunk_data_pos = ftell(f);
        if (chunk_data_pos < 0) {
            snprintf(error, error_size, "failed to read chunk position");
            fclose(f);
            return 0;
        }

        if (memcmp(chunk_header, "fmt ", 4) == 0) {
            if (chunk_size < 16) {
                snprintf(error, error_size, "fmt chunk is too small");
                fclose(f);
                return 0;
            }
            unsigned char fmt[16];
            if (!read_exact(f, fmt, sizeof(fmt))) {
                snprintf(error, error_size, "failed to read fmt chunk");
                fclose(f);
                return 0;
            }
            wav->audio_format = read_le16(fmt);
            wav->channels = read_le16(fmt + 2);
            wav->sample_rate = read_le32(fmt + 4);
            block_align = read_le16(fmt + 12);
            wav->bits_per_sample = read_le16(fmt + 14);
            have_fmt = 1;
            if (chunk_size > 16 && !skip_bytes(f, chunk_size - 16)) {
                snprintf(error, error_size, "failed to skip extended fmt bytes");
                fclose(f);
                return 0;
            }
        } else if (memcmp(chunk_header, "data", 4) == 0) {
            wav->data_size = chunk_size;
            data_offset = (uint32_t)chunk_data_pos;
            have_data = 1;
            if (!skip_bytes(f, chunk_size)) {
                snprintf(error, error_size, "failed to skip data chunk");
                fclose(f);
                return 0;
            }
        } else {
            if (!skip_bytes(f, chunk_size)) {
                snprintf(error, error_size, "failed to skip unknown chunk");
                fclose(f);
                return 0;
            }
        }
        if (have_fmt && have_data) {
            break;
        }
    }

    if (!have_fmt || !have_data) {
        snprintf(error, error_size, "missing required fmt or data chunk");
        fclose(f);
        return 0;
    }
    if (!(wav->audio_format == 1 || wav->audio_format == 3)) {
        snprintf(error, error_size, "unsupported WAV audio format: %u", wav->audio_format);
        fclose(f);
        return 0;
    }
    if (!(wav->channels == 1 || wav->channels == 2)) {
        snprintf(error, error_size, "unsupported channel count: %u", wav->channels);
        fclose(f);
        return 0;
    }
    if (!(wav->bits_per_sample == 16 || wav->bits_per_sample == 24 || wav->bits_per_sample == 32)) {
        snprintf(error, error_size, "unsupported bit depth: %u", wav->bits_per_sample);
        fclose(f);
        return 0;
    }
    if (wav->audio_format == 3 && wav->bits_per_sample != 32) {
        snprintf(error, error_size, "only 32-bit IEEE float WAV is supported");
        fclose(f);
        return 0;
    }
    uint16_t bytes_per_sample = (uint16_t)(wav->bits_per_sample / 8);
    uint16_t expected_block_align = (uint16_t)(wav->channels * bytes_per_sample);
    if (block_align != expected_block_align) {
        snprintf(error, error_size, "block align mismatch");
        fclose(f);
        return 0;
    }
    if (wav->data_size % block_align != 0) {
        snprintf(error, error_size, "data chunk size is not aligned to frames");
        fclose(f);
        return 0;
    }

    wav->frame_count = wav->data_size / block_align;
    size_t sample_count = (size_t)wav->frame_count * wav->channels;
    wav->samples = (float *)calloc(sample_count, sizeof(float));
    if (!wav->samples) {
        snprintf(error, error_size, "out of memory while loading samples");
        fclose(f);
        return 0;
    }
    if (fseek(f, (long)data_offset, SEEK_SET) != 0) {
        snprintf(error, error_size, "failed to seek to data chunk");
        wav_free(wav);
        fclose(f);
        return 0;
    }

    unsigned char sample_bytes[4];
    for (size_t i = 0; i < sample_count; i++) {
        if (!read_exact(f, sample_bytes, bytes_per_sample)) {
            snprintf(error, error_size, "unexpected EOF while reading samples");
            wav_free(wav);
            fclose(f);
            return 0;
        }
        wav->samples[i] = wav->audio_format == 3
            ? float32_to_float(sample_bytes)
            : pcm_to_float(sample_bytes, wav->bits_per_sample);
    }

    fclose(f);
    return 1;
}

static WAV_UNUSED int wav_write_float32(const char *path, const WavData *wav, const float *samples, uint32_t frame_count, char *error, size_t error_size) {
    FILE *f = fopen(path, "wb");
    if (!f) {
        snprintf(error, error_size, "failed to open output '%s': %s", path, strerror(errno));
        return 0;
    }

    uint16_t channels = wav->channels;
    uint32_t sample_rate = wav->sample_rate;
    uint16_t bits_per_sample = 32;
    uint16_t block_align = (uint16_t)(channels * 4);
    uint32_t byte_rate = sample_rate * block_align;
    uint32_t data_size = frame_count * block_align;
    uint32_t riff_size = 36 + data_size;

    fwrite("RIFF", 1, 4, f);
    write_le32(f, riff_size);
    fwrite("WAVE", 1, 4, f);
    fwrite("fmt ", 1, 4, f);
    write_le32(f, 16);
    write_le16(f, 3);
    write_le16(f, channels);
    write_le32(f, sample_rate);
    write_le32(f, byte_rate);
    write_le16(f, block_align);
    write_le16(f, bits_per_sample);
    fwrite("data", 1, 4, f);
    write_le32(f, data_size);

    size_t sample_count = (size_t)frame_count * channels;
    for (size_t i = 0; i < sample_count; i++) {
        float value = clamp_sample(samples[i]);
        if (fwrite(&value, sizeof(float), 1, f) != 1) {
            snprintf(error, error_size, "failed while writing audio samples");
            fclose(f);
            return 0;
        }
    }

    if (fclose(f) != 0) {
        snprintf(error, error_size, "failed to close output '%s'", path);
        return 0;
    }
    return 1;
}

static WAV_UNUSED double linear_to_db(double value) {
    if (value <= 0.0) {
        return -INFINITY;
    }
    return 20.0 * log10(value);
}

static WAV_UNUSED int wav_file_size_matches_data(const char *path, const WavData *wav) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        return 0;
    }
    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return 0;
    }
    long size = ftell(f);
    fclose(f);
    if (size < 44) {
        return 0;
    }
    return (uint32_t)size >= wav->data_size + 44;
}

#endif
