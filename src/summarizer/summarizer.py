import os
import getpass


# NOTE 
# There are 2 methods to load html file. For details, please see https://python.langchain.com/docs/integrations/document_loaders/
from langchain_community.document_loaders import UnstructuredHTMLLoader
# from langchain_community.document_loaders import BSHTMLLoader

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing_extensions import List, TypedDict

from langchain_ollama import OllamaEmbeddings, OllamaLLM
embeddings = OllamaEmbeddings(model="nomic-embed-text")
# local_llm = OllamaLLM(model="llama3.2", temperature=0.6)
# local_llm = OllamaLLM(model="llama3.2")
local_llm = OllamaLLM(model="deepseek-r1:1.5b")


# from langchain_community.vectorstores import FAISS

# from langchain_chroma import Chroma
# vector_store = Chroma(embedding_function=embeddings)

from langchain_core.vectorstores import InMemoryVectorStore
vector_store = InMemoryVectorStore(embeddings)

from langchain import hub

from langgraph.graph import START, StateGraph


# 获取当前文件所在目录
current_dir = os.path.dirname(__file__)

# 构建mails目录的完整路径
base_dir = os.path.join(current_dir, "..", "..", "temp", "mails")

def load_page_content(email_dir):
    html_files = [f for f in os.listdir(email_dir) if f.endswith('.html')]
    if not html_files:
        return None
        
    html_file_path = os.path.join(email_dir, html_files[0])
    
    loader = UnstructuredHTMLLoader(html_file_path)
    # loader = BSHTMLLoader(html_file_path)

    documents = loader.load()

    content = Document(documents[0].page_content)

    # test
    # print(50*'*')
    # print(content)
    # print(50*'*')

    return content
    


def load_all_page_content(base_dir):
    all_content = []
    # 确保目录存在
    if not os.path.exists(base_dir):
        print(f"Directory {base_dir} does not exist")
        return all_content
        
    # 遍历每个邮件目录
    for email_dir in os.listdir(base_dir):
        full_path = os.path.join(base_dir, email_dir)
        
        # 只处理目录
        if not os.path.isdir(full_path):
            continue
            
        content = load_page_content(full_path)
        if content:
            all_content.append(content)
            
    return all_content
    


all_mail_content = load_all_page_content(base_dir)


# text_splitter = RecursiveCharacterTextSplitter(
#     chunk_size = 1000,  # chunk size (characters)
#     chunk_overlap = 200,  # chunk overlap (characters)
#     add_start_index = True,  # track index in original document
# )

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,        # 邮件通常比普通文本更短，适当增大块大小
    chunk_overlap=200,      # 适当的重叠以保持上下文
    separators=["\n\n", "\n", " ", ""],  # 按换行、空格优先拆分
    add_start_index=True    # 记录原始位置
)

all_splits = text_splitter.split_documents(all_mail_content)

# test_split
# print(f"Split blog post into {len(all_splits)} sub-documents.")
# for split in all_splits:
#     print(split)

# vector_store = FAISS.from_documents(all_splits, embeddings)
# Index chunks
document_ids = vector_store.add_documents(documents=all_splits) 

# test_vector_storing
# print(document_ids[:3])

prompt = hub.pull("rlm/rag-prompt")

class State(TypedDict):
    question: str
    context: List[Document]
    answer: str

def retrieve(state: State):
    retrieved_docs = vector_store.similarity_search(state["question"])
    return {"context": retrieved_docs}


def generate(state: State):
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    messages = prompt.invoke({"question": state["question"], "context": docs_content})
    response = local_llm.invoke(messages)
    return {"answer": response}

# Compile application and test
graph_builder = StateGraph(State).add_sequence([retrieve, generate])
graph_builder.add_edge(START, "retrieve")
graph = graph_builder.compile()

# response = graph.invoke({"question": "Summarize and then use the summary to draft a podcast script."})
# response = graph.invoke({"question": "Summarize the content"})
# response = graph.invoke({"question": "Use the content to draft a podcast script."})
response = graph.invoke({"question": "Draft a podcast script based on the content."})
print(response["answer"])


