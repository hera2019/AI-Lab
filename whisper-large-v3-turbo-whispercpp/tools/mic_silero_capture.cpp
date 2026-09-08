#include "common-sdl.h"
#include "ggml-backend.h"
#include "whisper.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <csignal>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <fstream>
#include <string>
#include <thread>
#include <vector>

namespace {

constexpr int sample_rate = 16000;
constexpr int frame_samples = 1024; // 64 ms from the SDL callback
constexpr int pre_roll_frames = 5;  // 320 ms
constexpr int speech_start_frames = 2; // 128 ms, suitable for quiet speech
constexpr int silence_end_frames = 13; // 832 ms
constexpr int trailing_silence_frames = 4; // keep 256 ms
constexpr int maximum_speech_frames = 313; // about 20 seconds

std::atomic_bool running{true};

void handle_signal(int) {
    running = false;
}

void silent_log(enum ggml_log_level, const char *, void *) {
}

void write_u16(std::ofstream & output, uint16_t value) {
    const char bytes[2] = {
        static_cast<char>(value & 0xff),
        static_cast<char>((value >> 8) & 0xff),
    };
    output.write(bytes, sizeof(bytes));
}

void write_u32(std::ofstream & output, uint32_t value) {
    const char bytes[4] = {
        static_cast<char>(value & 0xff),
        static_cast<char>((value >> 8) & 0xff),
        static_cast<char>((value >> 16) & 0xff),
        static_cast<char>((value >> 24) & 0xff),
    };
    output.write(bytes, sizeof(bytes));
}

bool write_wav(const std::string & path, const std::vector<float> & samples) {
    std::ofstream output(path, std::ios::binary);
    if (!output) {
        return false;
    }

    const uint32_t data_size = static_cast<uint32_t>(samples.size() * sizeof(int16_t));
    output.write("RIFF", 4);
    write_u32(output, 36 + data_size);
    output.write("WAVE", 4);
    output.write("fmt ", 4);
    write_u32(output, 16);
    write_u16(output, 1);
    write_u16(output, 1);
    write_u32(output, sample_rate);
    write_u32(output, sample_rate * sizeof(int16_t));
    write_u16(output, sizeof(int16_t));
    write_u16(output, 16);
    output.write("data", 4);
    write_u32(output, data_size);

    for (const float sample : samples) {
        const float limited = std::max(-1.0f, std::min(1.0f, sample));
        const auto pcm = static_cast<int16_t>(std::lrint(limited * 32767.0f));
        write_u16(output, static_cast<uint16_t>(pcm));
    }
    return output.good();
}

float root_mean_square(const std::vector<float> & samples) {
    if (samples.empty()) {
        return 0.0f;
    }
    double sum = 0.0;
    for (const float sample : samples) {
        sum += static_cast<double>(sample) * sample;
    }
    return static_cast<float>(std::sqrt(sum / samples.size()));
}

} // namespace

int main(int argc, char ** argv) {
    std::string vad_model;
    std::string output_dir;
    int capture_id = -1;
    float threshold = 0.50f;

    for (int i = 1; i < argc; ++i) {
        const std::string argument = argv[i];
        if ((argument == "--vad-model" || argument == "-vm") && i + 1 < argc) {
            vad_model = argv[++i];
        } else if (argument == "--output-dir" && i + 1 < argc) {
            output_dir = argv[++i];
        } else if (argument == "--capture" && i + 1 < argc) {
            capture_id = std::stoi(argv[++i]);
        } else if (argument == "--threshold" && i + 1 < argc) {
            threshold = std::stof(argv[++i]);
        } else if (argument == "--help" || argument == "-h") {
            std::printf(
                "usage: %s --vad-model FILE --output-dir DIR "
                "[--capture ID] [--threshold N]\n",
                argv[0]);
            return 0;
        } else {
            std::fprintf(stderr, "unknown or incomplete argument: %s\n", argument.c_str());
            return 2;
        }
    }

    if (vad_model.empty() || output_dir.empty()) {
        std::fprintf(stderr, "--vad-model and --output-dir are required\n");
        return 2;
    }

    std::signal(SIGINT, handle_signal);
    std::signal(SIGTERM, handle_signal);
    whisper_log_set(silent_log, nullptr);
    ggml_backend_load_all();

    whisper_vad_context_params context_params = whisper_vad_default_context_params();
    context_params.n_threads = 4;
    context_params.use_gpu = false;
    whisper_vad_context * vad = whisper_vad_init_from_file_with_params(
        vad_model.c_str(), context_params);
    if (vad == nullptr) {
        std::fprintf(stderr, "failed to load Silero VAD model\n");
        return 3;
    }

    audio_async audio(2000);
    if (!audio.init(capture_id, sample_rate) || !audio.resume()) {
        whisper_vad_free(vad);
        return 4;
    }

    std::deque<std::vector<float>> pre_roll;
    std::vector<float> utterance;
    int consecutive_speech = 0;
    int consecutive_silence = 0;
    int utterance_frames = 0;
    int sequence = 0;
    bool in_speech = false;
    float peak_probability = 0.0f;
    int level_counter = 0;

    const auto emit_utterance = [&]() {
        if (utterance.empty()) {
            return;
        }
        if (consecutive_silence > trailing_silence_frames) {
            const size_t remove_samples = static_cast<size_t>(
                consecutive_silence - trailing_silence_frames) * frame_samples;
            if (remove_samples < utterance.size()) {
                utterance.resize(utterance.size() - remove_samples);
            }
        }
        const std::string path = output_dir + "/utterance-" +
            std::to_string(sequence++) + ".wav";
        if (!write_wav(path, utterance)) {
            std::fprintf(stderr, "failed to write utterance: %s\n", path.c_str());
            return;
        }
        const double seconds = static_cast<double>(utterance.size()) / sample_rate;
        std::printf("SEGMENT\t%s\t%.3f\t%.4f\n", path.c_str(), seconds, peak_probability);
        std::fflush(stdout);
    };

    while (running && sdl_poll_events()) {
        std::vector<float> captured;
        audio.get(1000, captured);
        if (captured.size() < frame_samples) {
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
            continue;
        }
        audio.clear();

        const size_t complete = captured.size() / frame_samples;
        const size_t first = captured.size() - complete * frame_samples;
        for (size_t frame_index = 0; frame_index < complete; ++frame_index) {
            const auto begin = captured.begin() + first + frame_index * frame_samples;
            std::vector<float> frame(begin, begin + frame_samples);
            if (!whisper_vad_detect_speech_no_reset(vad, frame.data(), frame.size())) {
                std::fprintf(stderr, "Silero VAD inference failed\n");
                running = false;
                break;
            }

            const int probability_count = whisper_vad_n_probs(vad);
            const float * probabilities = whisper_vad_probs(vad);
            float probability = 0.0f;
            for (int probability_index = 0;
                 probability_index < probability_count;
                 ++probability_index) {
                probability = std::max(probability, probabilities[probability_index]);
            }

            if (++level_counter >= 2) {
                std::printf(
                    "LEVEL\t%.5f\t%.4f\n",
                    root_mean_square(frame), probability);
                std::fflush(stdout);
                level_counter = 0;
            }

            if (!in_speech) {
                pre_roll.push_back(frame);
                while (static_cast<int>(pre_roll.size()) > pre_roll_frames) {
                    pre_roll.pop_front();
                }
                if (probability >= threshold) {
                    ++consecutive_speech;
                } else {
                    consecutive_speech = 0;
                }
                if (consecutive_speech >= speech_start_frames) {
                    in_speech = true;
                    utterance.clear();
                    for (const auto & previous : pre_roll) {
                        utterance.insert(
                            utterance.end(), previous.begin(), previous.end());
                    }
                    utterance_frames = static_cast<int>(pre_roll.size());
                    pre_roll.clear();
                    consecutive_silence = 0;
                    peak_probability = probability;
                }
                continue;
            }

            utterance.insert(utterance.end(), frame.begin(), frame.end());
            ++utterance_frames;
            peak_probability = std::max(peak_probability, probability);
            if (probability >= threshold) {
                consecutive_silence = 0;
            } else {
                ++consecutive_silence;
            }

            if (consecutive_silence >= silence_end_frames ||
                utterance_frames >= maximum_speech_frames) {
                emit_utterance();
                whisper_vad_reset_state(vad);
                in_speech = false;
                consecutive_speech = 0;
                consecutive_silence = 0;
                utterance_frames = 0;
                peak_probability = 0.0f;
                utterance.clear();
                pre_roll.clear();
            }
        }
    }

    if (in_speech && utterance_frames >= speech_start_frames) {
        emit_utterance();
    }
    audio.pause();
    whisper_vad_free(vad);
    return 0;
}
