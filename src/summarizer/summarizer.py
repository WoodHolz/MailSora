import os
import getpass


# NOTE 
# There are 2 methods to load html file. For details, please see https://python.langchain.com/docs/integrations/document_loaders/
from langchain_community.document_loaders import UnstructuredHTMLLoader
# from langchain_community.document_loaders import BSHTMLLoader
# from langchain_community.document_loaders import MHTMLLoader

# from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing_extensions import TypedDict

from langchain_ollama import OllamaEmbeddings, OllamaLLM
#embeddings = OllamaEmbeddings(model="nomic-embed-text")
# local_llm = OllamaLLM(model="llama3.2", temperature=0.6)
# local_llm = OllamaLLM(model="llama3.2")
local_llm = OllamaLLM(model="deepscaler")
# local_llm = OllamaLLM(model="openthinker")
# local_llm = OllamaLLM(model="qwen2.5:0.5b")
# local_llm = OllamaLLM(model="deepseek-r1:1.5b")

from langchain_deepseek import ChatDeepSeek
if not os.environ.get("DEEPSEEK_API_KEY"):
    os.environ["DEEPSEEK_API_KEY"] = getpass.getpass("Enter API key for Deepseek: ")

llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    streaming=True
    # other params..
)

from langchain import hub

from langsmith import traceable

from langgraph.graph import START, StateGraph

from bs4 import BeautifulSoup

from langchain_core.prompts import PromptTemplate

# 获取当前文件所在目录
current_dir = os.path.dirname(__file__)

# path of temp_dir
tmp_dir = os.path.join(current_dir, "..", "..", "temp")

# 构建mails目录的完整路径
base_dir = os.path.join(tmp_dir, "mails")

podcast_path = os.path.join(current_dir, "..", "podcast_generator")

def load_page_content(email_dir):
    html_files = [f for f in os.listdir(email_dir) if f.endswith('.html')]
    if not html_files:
        return None
        
    html_file_path = os.path.join(email_dir, html_files[0])
    
    loader = UnstructuredHTMLLoader(html_file_path)
    # loader = BSHTMLLoader(html_file_path)

    documents = loader.load()

    subject = os.path.basename(email_dir)

    # print("tile:", subject)
    # tests
    # print(50*'*')
    # for doc in documents:
    #     print(doc)
    # print(50*'*')

    content = Document(page_content=documents[0].page_content, metadata={"subject": subject})
    # content = Document(page_content=documents[0].page_content)
    
    # test
    # print(50*'*')
    # print(content)
    # print(50*'*')

    return content


def load_all_page_content(base_dir):
    all_content = []
    print(f"\nChecking directory: {base_dir}")
    # 确保目录存在
    if not os.path.exists(base_dir):
        print(f"Directory {base_dir} does not exist")
        return all_content
        
    # 遍历每个邮件目录
    dir_items = os.listdir(base_dir)
    print(f"Found {len(dir_items)} items in directory")
    
    for email_dir in dir_items:
        full_path = os.path.join(base_dir, email_dir)
        
        # 只处理目录
        if not os.path.isdir(full_path):
            print(f"Skipping non-directory: {email_dir}")
            continue
            
        print(f"Processing directory: {email_dir}")
        content = load_page_content(full_path)
        if content:
            all_content.append(content)
            print(f"Added content from: {email_dir}")
        else:
            print(f"No content found in: {email_dir}")
            
    print(f"Total content items found: {len(all_content)}")
    return all_content
    
prompt_template = """Generate a detailed podcast script in English for two hosts (Host 1 and Host 2) based on the provided email content and topic.

Instructions:
1. The script should be a dialogue between Host 1 and Host 2. Assign lines clearly (e.g., "Host 1:", "Host 2:").
2. Follow the specified format.
3. Return only the final script without any thought process or additional commentary.
4. Add appropriate pause markers like `[Pause]` or blank lines between speaker turns or significant topic shifts.
5. Ensure the script contains only clear, natural English text, avoiding special characters, mixed languages, or hard-to-pronounce words.
6. Make the conversation engaging and natural-sounding.


Email Content:
{context}

Topic:
{topic}

Podcast Script:
"""


prompt = PromptTemplate(template=prompt_template, input_variables=["context", "topic"])

class State(TypedDict):
    topic: str
    answer: str
    content: list

def run_summarizer(topic):
    print("\nStarting summarization process...")
    # Load content here instead of at module level
    all_mail_content = load_all_page_content(base_dir)
    
    if not all_mail_content:
        print("No email content found to summarize!")
        return None
    
    print(f"Found {len(all_mail_content)} emails to process")
    
    # Create graph with content
    def generate(state: State, **kwargs):
        print("Generating content from emails...")
        docs_content = "\n\n".join(doc.page_content for doc in all_mail_content)
        messages = {"context": docs_content, "topic": state["topic"]}
        print("Calling LLM for summary generation...")
        response = llm.invoke(prompt.format(**messages))
        return {"answer": response.content if hasattr(response, 'content') else str(response)}

    graph_builder = StateGraph(State).add_sequence([generate])
    graph_builder.add_edge(START, "generate")
    graph = graph_builder.compile()
    
    print("Running graph to generate summary...")
    response = graph.invoke({"topic": topic})
    print("Summary generation completed!")
    
    script = response["answer"]
    save_script(script)
    print("Script saved successfully!")
    
    return script

def save_script(script, file_path= os.path.join(podcast_path, "podcast_script.txt")):
    if os.path.exists(file_path):
        print(f"File '{file_path}' already exists, overwriting previous content...")
    if not isinstance(script, str):
        script = script.content
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"Script saved to {file_path}")

if __name__ == "__main__":
    run_summarizer(topic="news, tech blogs, Job alerts")