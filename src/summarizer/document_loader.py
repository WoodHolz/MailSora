import os
from langchain_community.document_loaders import UnstructuredHTMLLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
# from langchain_core.vectorstores import InMemoryVectorStore
from langchain_community.vectorstores import FAISS
from typing import List
import getpass
import pickle

# Configuration for embeddings and vector store
from langchain_ollama import OllamaEmbeddings

embeddings = OllamaEmbeddings(model="nomic-embed-text")
# vector_store = InMemoryVectorStore(embeddings)

# 获取当前文件所在目录
current_dir = os.path.dirname(__file__)

# 构建临时目录的完整路径
tmp_dir = os.path.join(current_dir, "..", "..", "temp")

# 构建mails目录的完整路径
base_dir = os.path.join(tmp_dir, "mails")

def load_page_content(email_dir):
    html_files = [f for f in os.listdir(email_dir) if f.endswith('.html')]
    if not html_files:
        return None
        
    html_file_path = os.path.join(email_dir, html_files[0])
    
    loader = UnstructuredHTMLLoader(html_file_path)
    documents = loader.load()

    content = Document(page_content=documents[0].page_content)
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
    
def merge_documents(all_content):
    merged_content = ""
    for doc in all_content:
        merged_content += doc.page_content + "\n"  # 合并内容，用换行符分隔

    # 创建一个新的 Document 对象
    merged_document = Document(
        page_content=merged_content
    )
    return merged_document

def split_documents(all_mail_content):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,        # 邮件通常比普通文本更短，适当增大块大小
        chunk_overlap=200,      # 适当的重叠以保持上下文
        separators=["\n\n", "\n", " ", ""],  # 按换行、空格优先拆分
        add_start_index=True    # 记录原始位置
    )
    all_splits = text_splitter.split_documents([all_mail_content])
    return all_splits

def load_and_prepare_documents(base_dir):
    all_mail_content = merge_documents(load_all_page_content(base_dir))
    all_splits = split_documents(all_mail_content)

    # Index chunks
    vector_store = FAISS.from_documents(all_splits, embeddings)
    document_ids = vector_store.add_documents(documents=all_splits) 
        # Index chunks and save vector store to a file
    vector_store.add_documents(documents=all_splits)
    vector_store.save_local(os.path.join(tmp_dir, "vector_store_faiss"))
    return vector_store

load_and_prepare_documents(base_dir)

