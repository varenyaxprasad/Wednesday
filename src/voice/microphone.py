import sounddevice as sd

print("Available audio devices:")
print(sd.query_devices())

print("\n Recording... speak for 5 seconds!")

recording = sd.rec(
    int(5 * 44100),
    samplerate=44100,
    channels=1
)

sd.wait()

print("✅ Recording finished!")