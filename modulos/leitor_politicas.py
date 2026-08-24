import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb

CHROMA_PATH = "chroma_db"

def inicializar_base_vetorial(pasta_politicas="politicas") -> bool:
    if not os.path.exists(pasta_politicas):
        os.makedirs(pasta_politicas)
        return False

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name="politicas_seguranca")

    documentos = []
    for arquivo in os.listdir(pasta_politicas):
        caminho = os.path.join(pasta_politicas, arquivo)
        if arquivo.endswith('.pdf'):
            loader = PyPDFLoader(caminho)
            documentos.extend(loader.load())
        elif arquivo.endswith(('.txt', '.md')):
            loader = TextLoader(caminho, encoding='utf-8')
            documentos.extend(loader.load())

    if not documentos:
        return False

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_documents(documentos)

    ids = [f"doc_{i}" for i in range(len(chunks))]
    textos = [doc.page_content for doc in chunks]
    metadados = [doc.metadata for doc in chunks]

    collection.upsert(ids=ids, documents=textos, metadatas=metadados)
    return True

def buscar_contexto_relevante(query: str, n_resultados: int = 3) -> str:
    if not os.path.exists(CHROMA_PATH):
        return "Nenhum banco de dados RAG encontrado. Execute a indexação primeiro."

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name="politicas_seguranca")
    
    resultados = collection.query(query_texts=[query], n_results=n_resultados)
    
    contexto = ""
    if resultados and 'documents' in resultados and resultados['documents']:
        for doc in resultados['documents'][0]:
            contexto += f"\n--- TRECHO DA NORMA ---\n{doc}\n"
    return contexto if contexto else "Nenhuma política específica encontrada no RAG."