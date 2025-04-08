import os
import getpass
import re
import shutil

import torch
from TTS.api import TTS
import gradio as gr
from pydub import AudioSegment

# Get device
device = "cuda" if torch.cuda.is_available() else "cpu"

# 获取当前文件所在目录
current_dir = os.path.dirname(__file__)

# path of temp_dir
tmp_dir = os.path.join(current_dir, "..", "..", "temp")
# Ensure tmp_dir exists for temporary audio files
os.makedirs(tmp_dir, exist_ok=True)
# Define a dedicated directory for audio segments within tmp_dir
segment_dir = os.path.join(tmp_dir, "audio_segments")
os.makedirs(segment_dir, exist_ok=True)

podcast_path = os.path.join(current_dir, "..", "podcast_generator")

# Use FastPitch model which is confirmed to support multiple speakers
MODEL_NAME = "tts_models/en/vctk/fast_pitch"

# Speaker mapping for VCTK FastPitch
# VCTK uses specific speaker IDs with 'VCTK_' prefix
# p236 and p270 are known for clearer voice quality
SPEAKER_MAP = {
    "Host 1": "VCTK_p236",  # Female voice (clearer quality)
    "Host 2": "VCTK_p270",  # Male voice (clearer quality)
}
DEFAULT_SPEAKER = "VCTK_p236"  # Default if speaker not in map

# 如果上面的说话人组合效果不好，可以尝试这些替代组合：
# SPEAKER_MAP = {
#     "Host 1": "VCTK_p233",  # Alternative female voice
#     "Host 2": "VCTK_p254",  # Alternative male voice
# }

def clean_text(text):
    # 删除方括号内容（如 [Pause], [Intro Music Fades In]）
    text = re.sub(r'\\[.*?\\]', '', text)
    # 移除可能存在的引号
    text = text.strip(' "')
    # 替换换行符为空格 (Though input should already be single lines)
    text = text.replace('\\n', ' ')
    # 移除多余的空格
    text = ' '.join(text.split())
    return text

def load_script(file_path):
    """读取播客文稿并解析为(speaker, text)列表"""
    if not os.path.exists(file_path):
        print(f"Error: Transcript file '{file_path}' not found!")
        return [] # Return empty list on error

    parsed_script = []
    with open(file_path, "r", encoding="utf-8") as f:
        current_speaker = None
        current_text = ""
        for line in f:
            line_stripped = line.strip()
            if not line_stripped: # Skip empty lines
                continue

            # Revised combined regex: Handles optional **, spaces, (Name), colon, trailing **
            # Captures '1' or '2' in group 1
            match = re.match(r'^(?:\*\*)?\s*Host\s+(1|2)(?:\s*\([^)]*\))?\s*:\s*(?:\*\*)?', line_stripped, re.IGNORECASE)

            speaker = None
            text_content = line_stripped # Default to the whole line

            if match:
                host_number = match.group(1)
                speaker = f"Host {host_number}"
                # Extract text *after* the matched tag
                text_content = line_stripped[match.end():].strip()
            # elif host2_match: # No longer needed with combined regex

            # Clean the extracted text content
            cleaned_content = clean_text(text_content)

            if speaker:
                # If there was previous text for a different speaker or no speaker, add it first
                if current_speaker and current_text and current_speaker != speaker:
                    parsed_script.append((current_speaker, current_text.strip()))
                    current_text = "" # Reset text for the new speaker
                elif current_speaker is None and current_text:
                    # Handle potential leading text before first speaker
                    print(f"Warning: Skipping text before first speaker: {current_text.strip()}")
                    current_text = ""

                # Start or continue speaker line
                current_speaker = speaker
                if cleaned_content:
                    current_text += cleaned_content + " " # Add space for potential continuation

            elif current_speaker and cleaned_content:
                # Continuation of the previous speaker's line (if line didn't start with a tag)
                 current_text += cleaned_content + " "
            elif cleaned_content:
                 # Text without a speaker identified and no current speaker active
                 print(f"Warning: Skipping line without clear speaker: {line_stripped}")


        # Add the last spoken part
        if current_speaker and current_text:
            parsed_script.append((current_speaker, current_text.strip()))

    # Filter out entries with empty text potentially created by cleaning
    parsed_script = [(speaker, text) for speaker, text in parsed_script if text]

    # print("Parsed Script:", parsed_script) # For debugging
    return parsed_script

def gen_podcast(script_path=os.path.join(podcast_path, "podcast_script.txt"),
                output_filename=os.path.join(tmp_dir, "podcast_output.wav")):
    """Generates a podcast from a script file with multiple speakers using FastPitch."""
    print("Loading and parsing script...")
    parsed_script = load_script(script_path)
    if not parsed_script:
        print("Script is empty or could not be loaded.")
        return

    print(f"Initializing TTS model: {MODEL_NAME}")
    try:
        # First check if model exists and download if necessary
        print("Checking model availability...")
        TTS.list_models()  # This ensures the model cache is updated
        manager = TTS()  # Initialize manager
        if not any(MODEL_NAME in m for m in manager.list_models()):
            print(f"Model {MODEL_NAME} not found locally. Downloading...")
            manager.download_model(MODEL_NAME)
            print("Model downloaded successfully!")

        # Initialize FastPitch model
        print("Loading model...")
        tts = TTS(MODEL_NAME)
        tts.to(device)
        
        # Print available speakers for debugging
        print("Available speakers:", tts.speakers)
        
    except Exception as e:
        print(f"Error initializing TTS model: {e}")
        print("Please ensure you have a stable internet connection and try again.")
        return

    segment_files = []
    combined_audio = AudioSegment.empty()

    print("Generating audio segments...")
    # Clear previous segments if any
    if os.path.exists(segment_dir):
        shutil.rmtree(segment_dir)
    os.makedirs(segment_dir, exist_ok=True)

    for i, (speaker, text) in enumerate(parsed_script):
        if not text:  # Skip empty text segments
            continue
        segment_filename = os.path.join(segment_dir, f"segment_{i:03d}.wav")
        speaker_id = SPEAKER_MAP.get(speaker, DEFAULT_SPEAKER)
        print(f"Segment {i}: Speaker '{speaker}' (ID: {speaker_id})")
        print(f"Text: '{text[:100]}...'")  # Print first 100 chars of text
        try:
            # Generate audio for the segment with FastPitch
            tts.tts_to_file(
                text=text,
                file_path=segment_filename,
                speaker=speaker_id
            )
            # Load the generated segment and append it
            segment_audio = AudioSegment.from_wav(segment_filename)
            # Add a short pause between segments
            if i > 0:  # Don't add pause before first segment
                combined_audio += AudioSegment.silent(duration=500)  # 500ms pause
            combined_audio += segment_audio
            segment_files.append(segment_filename)
        except Exception as e:
            print(f"Error generating TTS for segment {i} (Speaker: {speaker_id}): {e}")
            print(f"Text: {text}")
            continue  # Skip this segment and continue with the next

    print("\nCombining audio segments...")
    try:
        # Export the final combined audio
        combined_audio.export(output_filename, format="wav")
        print(f"Successfully generated podcast: {output_filename}")
    except Exception as e:
        print(f"Error exporting combined audio: {e}")

    # Clean up temporary segment files
    print("Cleaning up temporary files...")
    for f in segment_files:
        try:
            os.remove(f)
        except OSError as e:
            print(f"Error removing temporary file {f}: {e}")
    # Optionally remove the segment directory if empty
    try:
        os.rmdir(segment_dir)
    except OSError:
        pass  # Directory might not be empty if errors occurred

if __name__ == "__main__":
    # Example usage: gen_podcast() will use default paths
    gen_podcast()

    # You can also specify paths:
    # gen_podcast(script_path="path/to/your/script.txt", output_filename="path/to/output.wav")