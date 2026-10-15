import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import wave

SAMPLE_RATE = 16000
RECORD_SECONDS = 10

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)


def listen_and_transcribe():

    print("🎙️ Speak now...")

    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32"
    )

    sd.wait()

    audio = np.squeeze(audio)

    with wave.open("recording.wav", "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)

        audio_int16 = (audio * 32767).astype(np.int16)
        wav.writeframes(audio_int16.tobytes())

    print(" Recording finished")
    print(" Transcribing...")

    segments, info = model.transcribe("recording.wav")

    text = ""

    for segment in segments:
        text += segment.text

    text = text.strip()

    print(" You said:", text)

    return text

if __name__ == "__main__":
    listen_and_transcribe()