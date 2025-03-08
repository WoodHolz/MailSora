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
VOCODER_NAME = "vocoder_models/en/ljspeech/univnet"

# Initialize TTS with the target model name
# tts = TTS(MODEL_NAME).to(device)

# Run TTS
# tts.tts_to_file(file_path="test.wav", text="Hello world!")
import re

def clean_script(text):
    # 删除方括号内容（音乐提示）
    text = re.sub(r'\[.*?\]', '', text)
    # 删除**角色标记**
    text = re.sub(r'\*\*.*?:\*\*', '', text)
    # 将[Pause]转换为静音标识（需TTS支持）
    text = re.sub(r'\[Pause\]', '<SILENCE 1s>', text)
    return text

def load_script(file_path):
    """读取播客文稿"""
    if not os.path.exists(file_path):
        print(f"Error: Transcript file '{file_path}' not found!")
        return "GG, script not found!"
    with open(file_path, "r", encoding="utf-8") as f:
        content = clean_script(f.read())
        # content = content.replace("-", "")
        return content

def text_to_speech(text, output_filename):
    tts = TTS(model_name=MODEL_NAME, vocoder_name=VOCODER_NAME, gpu=False).to(device)
    # tts = TTS(model_name=MODEL_NAME, vocoder_name=VOCODER_NAME, gpu=False).to(device)
    tts.tts_to_file(text=text, file_path=output_filename)
    print(f"Generated WAV file: {output_filename}")


def gen_podcast():
    script = load_script(os.path.join(podcast_path, "podcast_script.txt"))
    text_to_speech(script, os.path.join(tmp_dir, "test.wav"))

if __name__ == "__main__":
    gen_podcast()