import os
import getpass
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_deepseek import ChatDeepSeek
from langchain import hub
from langgraph.graph import START, StateGraph
from typing_extensions import TypedDict

from langchain_community.vectorstores import FAISS

embeddings = OllamaEmbeddings(model="nomic-embed-text")

# Initialize LLM and DeepSeek API key
local_llm = OllamaLLM(model="qwen2.5:0.5b")

if not os.environ.get("DEEPSEEK_API_KEY"):
    os.environ["DEEPSEEK_API_KEY"] = getpass.getpass("Enter API key for Deepseek: ")

llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

# 获取当前文件所在目录
current_dir = os.path.dirname(__file__)

tmp_dir = os.path.join(current_dir, "..", "..", "temp")

vector_store_dir = os.path.join(tmp_dir, "vector_store_faiss")

# Load and prepare documents (call the function from document_loader.py)
base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "temp", "mails")
# vector_store, all_splits = load_and_prepare_documents(base_dir)
vector_store = FAISS.load_local(
    vector_store_dir, embeddings, allow_dangerous_deserialization=True
)
# Load the RAG prompt
prompt = hub.pull("rlm/rag-prompt")

class State(TypedDict):
    question: str
    context: list
    answer: str

def retrieve(state: State, k: int = 4):
    retrieved_docs = vector_store.similarity_search(state["question"], k=k)
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

response = graph.invoke({"question": "Draft a podcast script based on the content.", "k": 20})
print(response["answer"])
