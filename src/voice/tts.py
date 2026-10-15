from kokoro import KPipeline
import soundfile as sf
import subprocess
import tempfile
import os

# Initialize Kokoro
pipeline = KPipeline(lang_code="a")


def speak(text):
    """
    Convert text to speech using Kokoro
    and play it through the Mac speakers.
    """

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        filename = f.name

    try:
        for _, _, audio in pipeline(
            text,
            voice="af_bella",
            speed=0.88
        ):
            sf.write(filename, audio, 24000)

        subprocess.run(["afplay", filename])

    finally:
        if os.path.exists(filename):
            os.remove(filename)


if __name__ == "__main__":
    speak("Good evening. I have been waiting for you.")