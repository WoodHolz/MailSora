import os
import getpass

import torch
from TTS.api import TTS
import gradio as gr

# Get device
device = "cuda" if torch.cuda.is_available() else "cpu"

# 获取当前文件所在目录
current_dir = os.path.dirname(__file__)

# path of temp_dir
tmp_dir = os.path.join(current_dir, "..", "..", "temp")

podcast_path = os.path.join(current_dir, "..", "podcast_generator")

# List available 🐸TTS models
# print(TTS().list_models())

MODEL_NAME = "tts_models/en/ljspeech/glow-tts"

# Initialize TTS with the target model name
# tts = TTS(MODEL_NAME).to(device)

# Run TTS
# tts.tts_to_file(file_path="test.wav", text="Hello world!")

def load_script(file_path):
    """读取播客文稿"""
    if not os.path.exists(file_path):
        print(f"Error: Transcript file '{file_path}' not found!")
        return "GG, script not found!"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        content = content.replace("-", "")

        return content

def text_to_speech(text, output_filename):
    tts = TTS(model_name=MODEL_NAME, gpu=False).to(device)
    tts.tts_to_file(text=text, file_path=output_filename)
    print(f"Generated WAV file: {output_filename}")

script = load_script(os.path.join(podcast_path, "podcast_script.txt"))

text_to_speech(script, os.path.join(tmp_dir, "test.wav"))