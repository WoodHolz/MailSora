import os
from time import sleep
from typing import Tuple, Optional, Dict, List
from src.email_fetcher.email_fetcher_api import gmail_fetch, fetcher_temp_path
from src.summarizer.summarizer import run_summarizer, save_script
from src.podcast_generator.podcast_generater import gen_podcast
from src.utils.mails_sorter import MailSorter
import gradio as gr
import json
import shutil

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
        classification_result, classification_stats = display_sorted_emails()  # 获取分类结果和统计
        status_messages.append("Email classification completed!")
        status_messages.append("\n分类结果：")
        status_messages.append(classification_result)

        status_messages.append("\nStarting summarization...")
        script = run_summarizer(topic_input)
        returned_path = save_script(script)
        script_path = None
        script_content = script  # 保存脚本内容
        
        # 处理脚本文件路径
        if isinstance(returned_path, str) and os.path.exists(returned_path):
            script_path = returned_path
            # 读取保存的文件内容
            with open(script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
        else:
            potential_script_path = os.path.join("temp", "podcast_script.txt")
            if os.path.exists(potential_script_path):
                script_path = potential_script_path
                # 读取保存的文件内容
                with open(script_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
            else:
                # 如果找不到文件，尝试直接保存脚本内容
                script_path = os.path.join("temp", "podcast_script.txt")
                os.makedirs(os.path.dirname(script_path), exist_ok=True)
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(script)
        
        status_messages.append(f"Podcast script generated and saved to {script_path}!")

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
                
        # Return the results
        result = "\n".join(status_messages)
        
        # 返回所有需要的值：状态、音频、脚本内容、分类结果、分类统计
        return result, output_audio_path, script_content, classification_result, classification_stats
            
    except Exception as e:
        error_msg = f"Error during processing: {str(e)}"
        print(error_msg)  # 打印错误信息以便调试
        return error_msg, None, None, None, None

def fetch_emails_step(user_id_input: str, query_input: str) -> str:
    """单步执行：获取邮件"""
    try:
        gmail_fetch(user_id_input, query_input)
        return "邮件获取成功！邮件已保存到 temp/mails 目录。"
    except Exception as e:
        return f"邮件获取失败：{str(e)}"

def generate_script_step(topic_input: str) -> Tuple[str, str]:
    """单步执行：生成文稿"""
    try:
        script = run_summarizer(topic_input)
        script_path = save_script(script)
        return "文稿生成成功！", script
    except Exception as e:
        return f"文稿生成失败：{str(e)}", ""

def generate_audio_step() -> Tuple[str, str]:
    """单步执行：生成播客音频"""
    try:
        gen_podcast()
        # 查找生成的音频文件
        expected_audio_path = os.path.join("temp", "podcast_output.wav")
        if os.path.exists(expected_audio_path):
            return "播客音频生成成功！", expected_audio_path
        
        # 如果在默认位置找不到，搜索temp目录
        temp_dir = "temp"
        if os.path.isdir(temp_dir):
            wav_files = [f for f in os.listdir(temp_dir) if f.endswith(".wav")]
            if wav_files:
                audio_path = os.path.join(temp_dir, wav_files[0])
                return "播客音频生成成功！", audio_path
        
        return "播客音频生成完成，但未找到音频文件。", None
    except Exception as e:
        return f"播客音频生成失败：{str(e)}", None

def delete_local_emails() -> str:
    """删除本地下载的邮件"""
    try:
        if os.path.exists(fetcher_temp_path):
            shutil.rmtree(fetcher_temp_path)
            os.makedirs(fetcher_temp_path)  # 重新创建空目录
            return "成功删除本地邮件！"
        return "没有找到本地邮件目录。"
    except Exception as e:
        return f"删除邮件时出错：{str(e)}"

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
                    delete_btn = gr.Button("删除本地邮件", variant="secondary")
                
                with gr.Column():
                    status_output = gr.Textbox(label="Status", lines=10)
                    audio_output = gr.Audio(label="Generated Podcast")
                    script_output = gr.Textbox(
                        label="Generated Script",
                        lines=15,
                        placeholder="生成的播客文稿将显示在这里..."
                    )

        # 单步执行标签页
        with gr.Tab("单步执行"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 步骤 1: 获取邮件")
                    step1_user_id = gr.Textbox(label="User ID", value="me")
                    step1_query = gr.Textbox(
                        label="Email Query",
                        value='("job alert" OR "medium" OR "联合早报" OR "eCHO") newer_than:3d'
                    )
                    step1_delete_btn = gr.Button("删除本地邮件", variant="secondary")
                    step1_btn = gr.Button("1. 获取邮件", variant="primary")
                    step1_output = gr.Textbox(label="步骤 1 状态", lines=2)

                with gr.Column(scale=1):
                    gr.Markdown("### 步骤 2: 生成文稿")
                    step2_topic = gr.Textbox(label="Podcast Topic", value="news, tech blogs, Job alerts")
                    step2_btn = gr.Button("2. 生成文稿", variant="primary")
                    step2_status = gr.Textbox(label="步骤 2 状态", lines=2)
                    step2_output = gr.Textbox(label="生成的文稿", lines=10)

                with gr.Column(scale=1):
                    gr.Markdown("### 步骤 3: 生成播客")
                    step3_btn = gr.Button("3. 生成播客", variant="primary")
                    step3_status = gr.Textbox(label="步骤 3 状态", lines=2)
                    step3_output = gr.Audio(label="生成的播客")
    
    # 设置按钮点击事件
    classify_btn.click(
        fn=display_sorted_emails,
        inputs=[],
        outputs=[classification_output, stats_output]
    )
    
    run_btn.click(
        fn=run_pipeline,
        inputs=[user_id, query, topic],
        outputs=[
            status_output,
            audio_output,
            script_output,
            classification_output,
            stats_output
        ]
    )

    # 添加删除邮件按钮的事件处理
    delete_btn.click(
        fn=delete_local_emails,
        inputs=[],
        outputs=[status_output]
    )

    # 单步执行的按钮事件
    step1_btn.click(
        fn=fetch_emails_step,
        inputs=[step1_user_id, step1_query],
        outputs=[step1_output]
    )

    step1_delete_btn.click(
        fn=delete_local_emails,
        inputs=[],
        outputs=[step1_output]
    )

    step2_btn.click(
        fn=generate_script_step,
        inputs=[step2_topic],
        outputs=[step2_status, step2_output]
    )

    step3_btn.click(
        fn=generate_audio_step,
        inputs=[],
        outputs=[step3_status, step3_output]
    )

if __name__ == "__main__":
    try:
        demo.launch(share=False)
    except Exception as e:
        print(f"Error launching Gradio: {e}")
        try:
            simple_interface = gr.Interface(
                fn=run_pipeline,
                inputs=["text", "text", "text"],
                outputs=["text", "audio", "text", "text", "json"],
                title="Email to Podcast Generator (Simple Mode)"
            )
            simple_interface.launch(share=False)
        except Exception as e2:
            print(f"Fatal error launching Gradio: {e2}")
            print("Falling back to command line mode")
            main()