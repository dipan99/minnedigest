from pathlib import Path
from openai import OpenAI
import random as rand

client = OpenAI()
speech_file_path = Path(__file__).parent / "speech.mp3"

voices = ["coral", "onyx", "nova", "sage"]
chosen_voices = voices[rand.randrange(0, 4)]

response = client.audio.speech.create(
    model="tts-1",
    voice=chosen_voices,
    input="A woman from Minnesota who most recently lived in North Carolina is among the victims who died after an American Airlines plane collided with an Army helicopter on Wednesday in Washington, D.C.A GoFundMe campaign said Wendy Jo Shaffer was killed in the crash.\nWords cannot truly express what Wendy Jo meant as a daughter, a sister, a friend, a wife and most importantly, a mother.\nPaige Buss, who said she is Shaffer\u2019s cousin, confirmed to MPR News that Shaffer is from Minnesota but declined to speak further.\nShe was the best wife, mother, and friend that anyone could ever hope for.\nWe will miss you more than words can express, Wendy Jo.",
)
response.stream_to_file(speech_file_path)
