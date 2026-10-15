from speech_to_text import listen_and_transcribe
from tts import speak


def main():
    text = listen_and_transcribe()

    if text:
        speak(f"You said {text}")


if __name__ == "__main__":
    main()