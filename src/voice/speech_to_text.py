import sounddevice as sd
import numpy as np
import wave
import torch
from faster_whisper import WhisperModel
from silero_vad import load_silero_vad, get_speech_timestamps


SAMPLE_RATE = 16000
CHUNK_SIZE = 512

# How long silence must continue before we stop recording
SILENCE_DURATION = 0.8

# Maximum time we'll allow one utterance to run
MAX_RECORD_SECONDS = 30


# -----------------------------
# Load models
# -----------------------------

print("🧠 Loading Whisper...")
whisper_model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

print("🧠 Loading Silero VAD...")
vad_model = load_silero_vad()


# -----------------------------
# Record audio
# -----------------------------

def record_until_silence():

    print("🎙️ Listening...")

    audio_data = []
    started_speaking = False

    silence_start = None

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=CHUNK_SIZE
    )

    with stream:

        while True:

            audio, _ = stream.read(CHUNK_SIZE)

            audio = audio[:, 0]

            audio_data.extend(audio)

            # Check speech on a larger recent window
            if len(audio_data) >= SAMPLE_RATE:

                recent_audio = np.array(
                    audio_data[-SAMPLE_RATE:],
                    dtype=np.float32
                )

                tensor = torch.from_numpy(recent_audio)

                speech_timestamps = get_speech_timestamps(
                    tensor,
                    vad_model,
                    sampling_rate=SAMPLE_RATE
                )

                speech_detected = len(speech_timestamps) > 0

                if speech_detected:

                    if not started_speaking:
                        print("🗣️ Speech detected")

                    started_speaking = True
                    silence_start = None

                elif started_speaking:

                    if silence_start is None:
                        silence_start = len(audio_data)

                    silence_duration = (
                        len(audio_data) - silence_start
                    ) / SAMPLE_RATE

                    if silence_duration >= SILENCE_DURATION:

                        print("🛑 Speech ended")
                        break

    return np.array(audio_data, dtype=np.float32)


# -----------------------------
# Speech → Text
# -----------------------------

def listen_and_transcribe():

    audio = record_until_silence()

    with wave.open("recording.wav", "wb") as wav:

        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)

        audio_int16 = (audio * 32767).astype(np.int16)

        wav.writeframes(audio_int16.tobytes())

    print(" Transcribing...")

    segments, info = whisper_model.transcribe(
        "recording.wav"
    )

    text = ""

    for segment in segments:
        text += segment.text

    text = text.strip()

    print(" You said:", text)

    return text


if __name__ == "__main__":
    listen_and_transcribe()