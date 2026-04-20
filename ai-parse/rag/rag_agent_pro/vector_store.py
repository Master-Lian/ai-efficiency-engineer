# vector_store.py – 向量数据库
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_OFFLINE'] = '1'
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter     
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from config import KNOWLEDGE_BASE, PERSIST_DIR, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, RETRIEVAL_K

def get_embeddings():
    # 使用本地缓存的模型路径，避免网络下载
    local_model_path = r"C:\Users\lenovo\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2\snapshots\*"
    import glob
    snapshot_paths = glob.glob(local_model_path)
    if snapshot_paths:
        model_path = snapshot_paths[0]
        print(f"使用本地模型: {model_path}")
    else:
        model_path = "sentence-transformers/all-MiniLM-L6-v2"
        print(f"使用远程模型: {model_path}")
    
    return HuggingFaceEmbeddings(
        model_name=model_path,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

def load_documents(base_path):
    """
    加载所有 PDF 和 DOCX 文件，返回 Document 列表
    """
    if not os.path.exists(base_path):
        raise ValueError(f"路径不存在: {base_path}")
    docs = []
    # 加载 PDF
    if os.path.exists(base_path):
        pdf_loader = DirectoryLoader(
            base_path,
            glob="**/*.pdf",
            loader_cls=PyPDFLoader,
            show_progress=True,
            use_multithreading=True,
            recursive=True
        )
        try:
            pdf_docs = pdf_loader.load()
            print(f"成功加载 {len(pdf_docs)} 个 PDF 文档（按页分割）")
            docs.extend(pdf_docs)
        except Exception as e:
            print(f"加载 PDF 失败: {e}")

    # 加载 DOCX（可选）
    if os.path.exists(base_path):
        docx_loader = DirectoryLoader(
            base_path,
            glob="**/*.docx",
            loader_cls=Docx2txtLoader,
            show_progress=True,
            use_multithreading=True,
            recursive=True
        )
        try:
            docx_docs = docx_loader.load()
            print(f"成功加载 {len(docx_docs)} 个 DOCX 文档")
            docs.extend(docx_docs)
        except Exception as e:
            print(f"加载 DOCX 失败（可能没有 docx 文件）: {e}")
        return docs

def build_vector_store():
    """
    构建向量数据库
    """
    embeddings = get_embeddings()
    raw_docs = load_documents("E:\廉令武研究生文件夹\学习资料\C_CPP_Materials")

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    doc_splits = text_splitter.split_documents(raw_docs)
    print(f"共分割 {len(doc_splits)} 个文档页/段")

    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        collection_name="cpp_knowledge",
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )
    print(f"向量数据库构建完成，共 {len(vectorstore)} 条向量")
    return vectorstore

def load_vector_store():
    if not os.path.exists(PERSIST_DIR) or not os.path.isdir(PERSIST_DIR):
        return None
    
    # 尝试使用本地模型，避免网络下载
    try:
        embeddings = get_embeddings()
        vectorstore = Chroma(
            collection_name="cpp_knowledge",
            embedding_function=embeddings,
            persist_directory=PERSIST_DIR,
        )
        print(f"向量数据库加载完成，共 {len(vectorstore)} 条向量")
        return vectorstore
    except Exception as e:
        print(f"加载向量数据库失败: {e}")
        # 如果加载失败，返回 None，让 get_retriever() 处理
        return None


def get_retriever():
    vectorstore = load_vector_store()
    if vectorstore is None:
        if os.path.exists(PERSIST_DIR) and os.path.isdir(PERSIST_DIR):
            print("向量库加载失败，正在重建...")
            try:
                vectorstore = build_vector_store()
            except Exception as e:
                print(f"重建向量库失败: {e}")
                raise
        else:
            print("未找到向量数据库，正在构建...")
            vectorstore = build_vector_store()
    return vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K})
