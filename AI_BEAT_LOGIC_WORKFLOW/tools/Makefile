CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Werror -O2
LDFLAGS ?= -lm

TOOLS = wav_analyzer wav_gain_stage wav_trim_fade wav_integrity_check
TEST_DIR = .test_artifacts
TEST_WAV = $(TEST_DIR)/dummy.wav
INVALID_FILE = $(TEST_DIR)/invalid.wav

.PHONY: all clean test

all: $(TOOLS)

wav_analyzer: wav_analyzer.c wav_common.h
	$(CC) $(CFLAGS) -o $@ wav_analyzer.c $(LDFLAGS)

wav_gain_stage: wav_gain_stage.c wav_common.h
	$(CC) $(CFLAGS) -o $@ wav_gain_stage.c $(LDFLAGS)

wav_trim_fade: wav_trim_fade.c wav_common.h
	$(CC) $(CFLAGS) -o $@ wav_trim_fade.c $(LDFLAGS)

wav_integrity_check: wav_integrity_check.c wav_common.h
	$(CC) $(CFLAGS) -o $@ wav_integrity_check.c $(LDFLAGS)

$(TEST_WAV):
	mkdir -p $(TEST_DIR)
	python3 -c 'import math,wave; sample_rate=48000; frames=sample_rate; wav=wave.open("$(TEST_WAV)","wb"); wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(sample_rate); [wav.writeframesraw(((0 if i < sample_rate // 4 else int(math.sin(2*math.pi*440*i/sample_rate)*12000)).to_bytes(2,"little",signed=True))*2) for i in range(frames)]; wav.close()'

test: all $(TEST_WAV)
	./wav_analyzer $(TEST_WAV) > $(TEST_DIR)/analysis.json
	python3 -m json.tool $(TEST_DIR)/analysis.json > /dev/null
	./wav_integrity_check $(TEST_WAV) > $(TEST_DIR)/integrity.json
	python3 -m json.tool $(TEST_DIR)/integrity.json > /dev/null
	./wav_gain_stage $(TEST_WAV) $(TEST_DIR)/gain.wav --target-peak-db -3.0
	./wav_trim_fade $(TEST_WAV) $(TEST_DIR)/trim.wav --start 0.1 --end 0.8 --fade-in 0.02 --fade-out 0.1
	printf 'not a wav\n' > $(INVALID_FILE)
	! ./wav_integrity_check $(INVALID_FILE) > $(TEST_DIR)/invalid.json 2> $(TEST_DIR)/invalid.err
	python3 -m json.tool $(TEST_DIR)/invalid.json > /dev/null

clean:
	rm -f $(TOOLS)
	rm -rf $(TEST_DIR)
