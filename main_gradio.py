import os
from time import sleep
from typing import Tuple, Optional, Dict, List
from src.email_fetcher.email_fetcher_api import gmail_fetch
from src.summarizer.summarizer import run_summarizer, save_script
from src.podcast_generator.podcast_generater import gen_podcast
from src.utils.mails_sorter import MailSorter
import gradio as gr
import json

def sort_emails() -> Dict[str, List[str]]:
    """运行邮件分类并返回结果"""
    sorter = MailSorter()
    return sorter.sort_emails()

def display_sorted_emails() -> Tuple[str, str]:
    """分类邮件并返回格式化的结果"""
    try:
        result = sort_emails()
        
        # 生成详细的分类结果文本
        total_files = sum(len(files) for files in result.values())
        details = [f"共处理文件数：{total_files}\n"]
        
        for category, files in result.items():
            if files:  # 只显示非空类别
                details.append(f"\n{category}（{len(files)}个）:")
                for file in files:
                    details.append(f"  - {file}")
        
        # 生成分类统计的 JSON
        stats = {
            "总文件数": total_files,
            "分类统计": {category: len(files) for category, files in result.items()}
        }
        
        return "\n".join(details), json.dumps(stats, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"邮件分类过程中出错：{str(e)}", "{}"

def main():
    # test
    user_id = "me"
    query = '("job alert" OR "medium" OR "联合早报" OR "eCHO") newer_than:3d'
    print("Starting email fetching...")
    # Step 1: Fetch emails
    gmail_fetch(user_id, query)
    
    print("Emails fetched successfully!")
    
    print("\nStarting summarization...")
    # Step 2: Generate podcast script
    topic = "news, tech blogs, Job alerts"
    script = run_summarizer(topic)
    save_script(script)
    print("Podcast script generated successfully!")
    
    # Step 3: Generate audio
    print("\nStarting audio generation...")
    # Get current directory
    # current_dir = os.path.dirname(__file__)
    # Define output paths
    # script_path = os.path.join(current_dir, "temp", "podcast_script.txt")
    # output_path = os.path.join(current_dir, "temp", "podcast_output.wav")
    
    gen_podcast()


def run_pipeline(user_id_input: str, query_input: str, topic_input: str):
    """Simplified version with minimal type hints to avoid Pydantic schema issues"""
    status_messages = []

    try:
        status_messages.append("Starting email fetching...")
        gmail_fetch(user_id_input, query_input)
        status_messages.append("Emails fetched successfully!")

        # 添加邮件分类步骤
        status_messages.append("\nStarting email classification...")
        classification_result, _ = display_sorted_emails()
        status_messages.append("Email classification completed!")
        status_messages.append("\n分类结果：")
        status_messages.append(classification_result)

        status_messages.append("\nStarting summarization...")
        script = run_summarizer(topic_input)
        returned_path = save_script(script)
        script_path = None
        
        if isinstance(returned_path, str) and os.path.exists(returned_path):
            script_path = returned_path
            status_messages.append(f"Podcast script generated and saved to {script_path}!")
        else:
            potential_script_path = os.path.join("temp", "podcast_script.txt")
            if os.path.exists(potential_script_path):
                script_path = potential_script_path
                status_messages.append(f"Podcast script generated and saved to {script_path}! (Path inferred)")
            else:
                status_messages.append("Podcast script generated, but path not confirmed or file not found.")

        status_messages.append("\nStarting audio generation...")
        gen_podcast()
        
        # Find the audio file
        output_audio_path = None
        expected_audio_path = os.path.join("temp", "podcast_output.wav")
        if os.path.exists(expected_audio_path):
            output_audio_path = expected_audio_path
            status_messages.append(f"Audio generated successfully! Output: {output_audio_path}")
        else:
            temp_dir = "temp"
            if os.path.isdir(temp_dir):
                wav_files = [f for f in os.listdir(temp_dir) if f.endswith(".wav")]
                if wav_files:
                    output_audio_path = os.path.join(temp_dir, wav_files[0])
                    status_messages.append(f"Audio generated successfully! Output: {output_audio_path} (found in temp)")
                else:
                    status_messages.append("Audio generation complete, but output file not found in temp directory.")
            else:
                status_messages.append(f"Audio generation complete, but temp directory '{temp_dir}' not found.")
                
        # Return the results - simplify this to avoid complex return types
        result = "\n".join(status_messages)
        return result, output_audio_path, script_path
    except Exception as e:
        return f"Error during processing: {str(e)}", None, None

# Create a simplified version of the Gradio interface
with gr.Blocks(title="Email to Podcast Generator") as demo:
    gr.Markdown("# Email to Podcast Generator")
    gr.Markdown("Fetches emails, classifies them, summarizes them, and generates a podcast.")
    
    with gr.Tabs():
        # 邮件分类标签页
        with gr.Tab("邮件分类"):
            with gr.Row():
                classify_btn = gr.Button("运行邮件分类", variant="primary")
            with gr.Row():
                with gr.Column():
                    classification_output = gr.Textbox(
                        label="分类结果", 
                        lines=10,
                        placeholder="点击'运行邮件分类'按钮查看结果..."
                    )
                with gr.Column():
                    stats_output = gr.JSON(
                        label="分类统计",
                        value={"总文件数": 0, "分类统计": {"工作": 0, "技术": 0, "新闻": 0, "其他": 0}}
                    )
        
        # 生成播客标签页
        with gr.Tab("生成播客"):
            with gr.Row():
                with gr.Column():
                    user_id = gr.Textbox(label="User ID", value="me")
                    query = gr.Textbox(
                        label="Email Query", 
                        value='("job alert" OR "medium" OR "联合早报" OR "eCHO") newer_than:3d'
                    )
                    topic = gr.Textbox(label="Podcast Topic", value="news, tech blogs, Job alerts")
                    run_btn = gr.Button("Generate Podcast", variant="primary")
                
                with gr.Column():
                    status_output = gr.Textbox(label="Status", lines=10)
                    audio_output = gr.Audio(label="Generated Podcast")
                    file_output = gr.File(label="Generated Script")
    
    # 设置按钮点击事件
    classify_btn.click(
        fn=display_sorted_emails,
        inputs=[],
        outputs=[classification_output, stats_output]
    )
    
    run_btn.click(
        fn=run_pipeline,
        inputs=[user_id, query, topic],
        outputs=[status_output, audio_output, file_output]
    )

if __name__ == "__main__":
    # main() # We'll launch the Gradio app instead
    try:
        demo.launch(share=False)
    except Exception as e:
        print(f"Error launching Gradio: {e}")
        # Attempt even simpler fallback if needed
        try:
            simple_interface = gr.Interface(
                fn=run_pipeline,
                inputs=["text", "text", "text"],
                outputs=["text", "audio", "file"],
                title="Email to Podcast Generator (Simple Mode)"
            )
            simple_interface.launch(share=False)
        except Exception as e2:
            print(f"Fatal error launching Gradio: {e2}")
            print("Falling back to command line mode")
            main()  # Run the regular main function as fallback