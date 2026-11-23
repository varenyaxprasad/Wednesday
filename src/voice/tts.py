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



def speak_long_text(text, max_chars=450):
    """Speak long responses in smaller chunks."""
    import re

    sentences = re.split(r'(?<=[.!?\n])\s+', text)
    chunk = ""

    for sentence in sentences:
        if len(chunk) + len(sentence) > max_chars and chunk:
            speak(chunk.strip())
            chunk = ""

        if len(sentence) > max_chars:
            if chunk:
                speak(chunk.strip())
                chunk = ""
            for i in range(0, len(sentence), max_chars):
                speak(sentence[i:i + max_chars])
        else:
            chunk += sentence + " "

    if chunk.strip():
        speak(chunk.strip())
        
if __name__ == "__main__":
    speak("Good evening. I have been waiting for you.")
    