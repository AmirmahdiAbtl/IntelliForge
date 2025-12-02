"""Vector database service"""
import os
from typing import List, Tuple
from langchain_community.document_loaders import PyPDFLoader, UnstructuredURLLoader
from langchain_community.vectorstores import FAISS, Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import config
from app.services.embedding_service import embedding_service


class VectorDBService:
    """Handle vector database operations"""
    
    def __init__(self):
        self.embedding_model = embedding_service.embedding_model
    
    def create_vectordb(self, documents: List[Tuple[str, str]], 
                       vector_store_type: str, chunk_size: int, 
                       index_name: str):
        """
        Create a vector database from documents
        
        Args:
            documents: List of (doc_type, path) tuples
            vector_store_type: 'faiss' or 'chroma'
            chunk_size: Size of text chunks
            index_name: Name for the vector store
        """
        index_path = os.path.join(config.VECTOR_DB_PATH, index_name)
        
        # Load all documents
        all_documents = []
        for doc_type, path in documents:
            try:
                if doc_type == "link":
                    loader = UnstructuredURLLoader(urls=[path])
                    docs = loader.load()
                elif doc_type == "pdf":
                    loader = PyPDFLoader(path)
                    docs = loader.load()
                elif doc_type == "text":
                    with open(path, "r", encoding="utf-8") as file:
                        content = file.read()
                        docs = [Document(page_content=content)]
                else:
                    print(f"Unsupported document type: {doc_type}")
                    continue
                
                all_documents.extend(docs)
            except Exception as e:
                print(f"Failed to load {doc_type}: {path} with error: {e}")
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=config.DEFAULT_CHUNK_OVERLAP
        )
        chunked_texts = [
            chunk 
            for doc in all_documents 
            for chunk in text_splitter.split_text(doc.page_content)
        ]
        
        # Create vector store
        if vector_store_type == "faiss":
            vectorstore = FAISS.from_texts(chunked_texts, self.embedding_model)
            vectorstore.save_local(index_path)
        elif vector_store_type == "chroma":
            vectorstore = Chroma.from_texts(
                texts=chunked_texts,
                embedding=self.embedding_model,
                persist_directory=index_path
            )
            vectorstore.persist()
        else:
            raise ValueError(f"Unsupported vector store type: {vector_store_type}")
        
        return vectorstore
    
    def load_vectordb(self, index_name: str, vector_store_type: str):
        """Load an existing vector database"""
        index_path = os.path.join(config.VECTOR_DB_PATH, index_name)
        
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"Vector store not found: {index_path}")
        
        if vector_store_type == "faiss":
            return FAISS.load_local(
                index_path, 
                self.embedding_model, 
                allow_dangerous_deserialization=True
            )
        elif vector_store_type == "chroma":
            return Chroma(
                persist_directory=index_path,
                embedding_function=self.embedding_model
            )
        else:
            raise ValueError(f"Unsupported vector store type: {vector_store_type}")


# Singleton instance
vector_db_service = VectorDBService()
