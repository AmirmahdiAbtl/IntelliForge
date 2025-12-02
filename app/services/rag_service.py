"""RAG service for RAG operations"""
from typing import List, Tuple, Dict
from app.repositories.rag_repository import RAGRepository
from app.services.vector_db_service import vector_db_service
from app.services.llm_service import llm_service


class RAGService:
    """Handle RAG business logic"""
    
    def __init__(self):
        self.repo = RAGRepository()
        self.vector_db_service = vector_db_service
        self.llm_service = llm_service
    
    def create_rag(self, name: str) -> int:
        """Create a new RAG project"""
        return self.repo.create_rag(name)
    
    def get_rag(self, rag_id: int) -> Dict:
        """Get RAG project"""
        rag = self.repo.get_rag(rag_id)
        if rag:
            rag['status'] = self._compute_status(rag, rag_id)
        return rag
    
    def get_all_rags(self) -> List[Dict]:
        """Get all RAG projects"""
        rags = self.repo.get_all_rags()
        for rag in rags:
            rag['status'] = self._compute_status(rag, rag['id'])
        return rags
    
    def update_model_config(self, rag_id: int, model_type: str, 
                          model_name: str, api_key: str):
        """Update RAG model configuration"""
        self.repo.update_rag_model(rag_id, model_type, model_name, api_key)
    
    def update_vector_db_config(self, rag_id: int, embedding_model:str, vector_db: str, chunk_size: int):
        """Update vector database configuration"""
        self.repo.update_rag_vector_db(rag_id, embedding_model, vector_db, chunk_size)
    
    def add_document(self, rag_id: int, doc_type: str, doc_path: str, description: str = ""):
        """Add a document to RAG"""
        self.repo.add_document(rag_id, doc_type, doc_path, description)
    
    def get_documents_with_descriptions(self, rag_id: int) -> List[Dict]:
        """Get all documents with descriptions for a RAG"""
        return self.repo.get_documents_with_descriptions(rag_id)
    
    def delete_document(self, rag_id: int, doc_path: str):
        """Delete a document from RAG"""
        self.repo.delete_document(rag_id, doc_path)
    
    def update_prompt_template(self, rag_id: int, prompt_template: str):
        """Update RAG prompt template"""
        self.repo.update_rag_prompt_template(rag_id, prompt_template)
    
    def _compute_status(self, rag: Dict, rag_id: int) -> str:
        """Compute RAG completion status"""
        # Check if all required fields are present
        if not rag.get('model_type') or not rag.get('model_name'):
            return 'incomplete'
        
        if not rag.get('vector_db') or not rag.get('chunk_size'):
            return 'incomplete'
        
        # Check if has documents
        documents = self.repo.get_documents(rag_id)
        if not documents:
            return 'incomplete'
        
        # Check if has prompt template
        if not rag.get('prompt_template'):
            return 'incomplete'
        
        return 'ready'
    
    def get_next_step_url(self, rag_id: int) -> str:
        """Get URL for next setup step"""
        from flask import url_for
        
        rag = self.repo.get_rag(rag_id)
        if not rag:
            return url_for('main.panel')
        
        # Step 1: Model Selection
        if not rag.get('model_type') or not rag.get('model_name'):
            return url_for('rag_creator.model_selection', rag_id=rag_id)
        
        # Step 2: Vector DB/Embedding Selection
        if not rag.get('vector_db') or not rag.get('chunk_size'):
            return url_for('rag_creator.db_embedding_selection', rag_id=rag_id)
        
        # Step 3: Document Upload
        documents = self.repo.get_documents(rag_id)
        if not documents:
            return url_for('rag_creator.documentation_upload', rag_id=rag_id)
        
        # Step 4: Prompt Template
        if not rag.get('prompt_template'):
            return url_for('rag_creator.prompt_template', rag_id=rag_id)
        
        # All steps complete
        return url_for('rag_creator.rag_details', rag_id=rag_id)
    
    def create_vector_database(self, rag_id: int):
        """Create vector database from RAG documents"""
        rag = self.repo.get_rag(rag_id)
        if not rag:
            raise ValueError("RAG not found")
        
        documents = self.repo.get_documents(rag_id)
        if not documents:
            raise ValueError(f"No documents found for RAG ID {rag_id}")
        
        vectorstore = self.vector_db_service.create_vectordb(
            documents,
            rag['vector_db'],
            rag['chunk_size'],
            f"rag_{rag_id}"
        )
        
        return vectorstore
    
    def query_rag(self, rag_id: int, query: str, chat_history: List[Tuple] = None):
        """Query RAG with conversational context"""
        rag = self.repo.get_rag(rag_id)
        if not rag:
            raise ValueError("RAG not found")
        
        # Load vector database
        vectorstore = self.vector_db_service.load_vectordb(
            f"rag_{rag_id}",
            rag['vector_db']
        )
        
        # Get LLM
        llm = self.llm_service.get_llm(
            rag['model_name'],
            rag['api_key'],
            rag['model_type']
        )
        
        # Create retrieval chain with custom prompt template and reranking
        chain = self.llm_service.create_retrieval_chain(
            llm, 
            vectorstore, 
            rag.get('prompt_template'),
            use_reranking=True,  # Enable reranking for better results
            top_k_retrieval=20,  # Retrieve more documents initially
            top_k_reranked=5     # Return top 5 after reranking
        )
        
        # Query
        result = chain({
            "question": query,
            "chat_history": chat_history or []
        })
        
        return result
    
    def create_chat_session(self, rag_id: int, session_name: str) -> int:
        """Create a chat session for RAG"""
        return self.repo.create_chat_session(rag_id, session_name)
    
    def get_chat_sessions(self, rag_id: int) -> List[Dict]:
        """Get all chat sessions for RAG"""
        return self.repo.get_chat_sessions(rag_id)
    
    def add_chat_message(self, session_id: int, user_message: str, bot_response: str, rag_id: int = None):
        """Add a message to chat session and generate name if first message"""
        # Check if this is the first message in the session
        history = self.repo.get_chat_history(session_id)
        
        # Generate chat name if first message
        if len(history) == 0 and rag_id:
            rag = self.repo.get_rag(rag_id)
            if rag and rag.get('model_type') and rag.get('model_name'):
                suggested_name = self.llm_service.generate_name(
                    rag['model_type'],
                    rag['model_name'],
                    user_message,
                    rag.get('api_key')
                )
                # Update the session name in database
                RAGRepository.update_chat_session_name(session_id, suggested_name)
        
        self.repo.add_chat_message(session_id, user_message, bot_response)
    
    def get_chat_history(self, session_id: int) -> List[Dict]:
        """Get chat history for session"""
        return self.repo.get_chat_history(session_id)


# Singleton instance
rag_service = RAGService()
