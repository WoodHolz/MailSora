import os
from pydoc import doc

# NOTE 
# There are 2 methods to load html file. For details, please see https://python.langchain.com/docs/integrations/document_loaders/
from langchain_community.document_loaders import UnstructuredHTMLLoader
# from langchain_community.document_loaders import BSHTMLLoader

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from langchain_ollama import OllamaEmbeddings
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# from langchain_community.vectorstores import FAISS

# from langchain_chroma import Chroma
# vector_store = Chroma(embedding_function=embeddings)

from langchain_core.vectorstores import InMemoryVectorStore
vector_store = InMemoryVectorStore(embeddings)


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


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = 512,  # chunk size (characters)
    chunk_overlap = 200,  # chunk overlap (characters)
    add_start_index = True,  # track index in original document
)

all_splits = text_splitter.split_documents(all_mail_content)

# test
print(f"Split blog post into {len(all_splits)} sub-documents.")
for split in all_splits:
    print(split)

# vector_store = FAISS.from_documents(all_splits, embeddings)
# Index chunks
document_ids = vector_store.add_documents(documents=all_splits) 

# test
print(document_ids[:3])


# 测试代码
# if __name__ == "__main__":
    # query = "job"
    # docs = vector_store.similarity_search(query)
    # print(40 * '+')
    # print(docs)

#     # 获取当前文件所在目录
#     current_dir = os.path.dirname(__file__)
#     # 构建mails目录的完整路径
#     base_dir = os.path.join(current_dir, "..", "..", "temp", "mails")
    
#     load_all_page_content(base_dir)

