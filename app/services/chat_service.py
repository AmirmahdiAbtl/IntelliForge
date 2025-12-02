"""Chat service for regular chat operations"""
import json
import time
import numpy as np
from datetime import datetime
from typing import List, Tuple, Dict
from app.repositories.chat_repository import ChatRepository
from app.services.embedding_service import embedding_service
from app.services.llm_service import llm_service
from app.services.web_search_service import web_search_service
# Token management constants
MAX_CONTEXT_TOKENS = 6000
MAX_RECENT_MESSAGES = 8  
MAX_SIMILAR_MESSAGES = 2
MAX_MESSAGE_LENGTH = 500
SIMILARITY_THRESHOLD = 0.3

class ChatService:
    """Handle chat business logic"""
    
    def __init__(self):
        self.repo = ChatRepository()
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.web_search_service = web_search_service
    
    def create_chat_session(self, name: str = "New Chat", 
                           language_model: str = 'pending',
                           model_type: str = 'ChatGPT', 
                           api_key: str = 'pending') -> int:
        """Create a new chat session"""
        return self.repo.create_chat_session(name, language_model, model_type, api_key)
    
    def get_chat_session(self, chat_id: int) -> Dict:
        """Get chat session"""
        return self.repo.get_chat_session(chat_id)
    
    def get_all_chat_sessions(self) -> List[Dict]:
        """Get all chat sessions"""
        return self.repo.get_all_chat_sessions()
    
    def update_chat_config(self, chat_id: int, language_model: str, 
                          model_type: str, api_key: str, 
                          temperature: float = 0.7):
        """Update chat configuration"""
        self.repo.update_chat_config(
            chat_id, language_model, model_type, api_key, temperature
        )
    
    def _get_optimized_history(self, history: List[Dict], user_input: str) -> List[Tuple[str, str]]:
        """Get optimized chat history to prevent token overflow"""
        if not history:
            return []
        
        # 1. Get recent messages (sliding window)
        recent_history = history[-MAX_RECENT_MESSAGES:] if len(history) > MAX_RECENT_MESSAGES else history
        
        formatted_history = []
        
        # 2. Add recent messages with truncation
        for msg in recent_history:
            prompt = msg['prompt'][:MAX_MESSAGE_LENGTH]
            response = msg['chat_response'][:MAX_MESSAGE_LENGTH]
            formatted_history.append((prompt, response))
        
        # 3. Add similar messages only if we have older messages
        if len(history) > MAX_RECENT_MESSAGES:
            try:
                query_embedding = self.embedding_service.generate_embedding(user_input)
                similarities = []
                
                # Only search in older messages (not recent ones)
                older_history = history[:-MAX_RECENT_MESSAGES]
                
                for msg in older_history:
                    if msg.get('embedding'):
                        try:
                            db_embedding = json.loads(msg['embedding'])
                            numerator = float(np.dot(query_embedding, db_embedding))
                            denominator = float(
                                np.linalg.norm(query_embedding) * 
                                np.linalg.norm(db_embedding) + 1e-8
                            )
                            similarity = numerator / denominator
                            
                            # Only add if similarity is meaningful
                            if similarity > SIMILARITY_THRESHOLD:
                                similarities.append({
                                    "prompt": msg['prompt'][:MAX_MESSAGE_LENGTH],
                                    "response": msg['chat_response'][:MAX_MESSAGE_LENGTH],
                                    "similarity": similarity
                                })
                        except (json.JSONDecodeError, ValueError):
                            continue
                
                # Add top similar messages
                sorted_results = sorted(similarities, key=lambda x: x["similarity"], reverse=True)
                for item in sorted_results[:MAX_SIMILAR_MESSAGES]:
                    formatted_history.append((item['prompt'], item['response']))
                    
            except Exception as e:
                print(f"Warning: Error in similarity search: {e}")
        
        return formatted_history
    
    def process_message(self, chat_id: int, user_input: str, web_search_enabled: bool = False) -> Dict:
        """Process a chat message and generate response"""
        start_time = time.time()
        
        # Get chat configuration
        config = self.repo.get_chat_config(chat_id)
        if not config:
            raise ValueError("Chat not found")
        
        if config['language_model'] == 'pending' or config['api_key'] == 'pending':
            raise ValueError("Please configure the chat model before sending messages")
        
        # Get chat history
        history = self.repo.get_chat_history(chat_id)
        
        # Generate chat name if first message
        if len(history) == 0:
            suggested_name = self.llm_service.generate_name(
                config['model_type'],
                config['language_model'],
                user_input,
                config['api_key']
            )
            self.repo.update_chat_name(chat_id, suggested_name)
        
        # Smart history management to prevent token overflow
        formatted_history = self._get_optimized_history(history, user_input)
        
        # Handle web search if enabled
        web_context = ""
        source_urls = []
        if web_search_enabled:
            try:
                # Enhance query for current events and factual information
                search_query = user_input
                if any(word in user_input.lower() for word in ['president', 'current', '2024', '2025', 'now', 'today', 'latest']):
                    search_query = f"{user_input} 2025 current latest"
                
                print(f"Performing web search for: {search_query}")
                web_context, source_urls = self.web_search_service.search_and_get_context_sync(search_query, num_results=5)
                print(f"Web search completed. Found {len(source_urls)} sources.")
            except Exception as e:
                print(f"Web search failed: {str(e)}")
                web_context = f"Web search temporarily unavailable: {str(e)}"
        
        # Create prompt template with optional web search context
        if web_search_enabled and web_context and "Web search encountered an error" not in web_context:
            if formatted_history:
                prompt_template = f"""Previous conversation context: {{chat_history}}

                **IMPORTANT: You MUST use the following web search results to answer the user's question. Do not ignore this information:**

                {web_context}

                **Instructions: Base your response primarily on the web search results above. If the web results contain current information, use that instead of your training data.**

                User: {{question}}
                Assistant:"""
            else:
                prompt_template = f"""**IMPORTANT: You MUST use the following web search results to answer the user's question. Do not ignore this information:**

                {web_context}

                **Instructions: Base your response primarily on the web search results above. If the web results contain current information, use that instead of your training data.**

                User: {{question}}
                Assistant:"""
        else:
            if formatted_history:
                prompt_template = """Previous conversation context: {chat_history}

                User: {question}
                Assistant:"""
            else:
                prompt_template = """User: {question}
                Assistant:"""
        
        # Check token limit before sending to model
        estimated_tokens = self._get_total_context_tokens(formatted_history, user_input, prompt_template)
        max_tokens = MAX_CONTEXT_TOKENS
        
        if estimated_tokens > max_tokens:
            # Further reduce history if still too large
            formatted_history = formatted_history[-4:] if len(formatted_history) > 4 else formatted_history
            print(f"Warning: Reduced context due to token limit. Estimated tokens: {estimated_tokens}")
        
        # Get LLM and generate response
        llm = self.llm_service.get_llm(
            config['language_model'],
            config['api_key'],
            config['model_type']
        )
        
        chat_chain = self.llm_service.create_chat_chain(
            llm, prompt_template, ["chat_history", "question"]
        )
        
        response = chat_chain.run(chat_history=formatted_history, question=user_input)
        
        # Add source URLs to response if web search was used
        if web_search_enabled and source_urls:
            sources_text = "\n\n**Sources:**\n" + "\n".join([f"• {url}" for url in source_urls])
            response += sources_text
        
        # Calculate metrics
        execution_time = int((time.time() - start_time) * 1000)
        response_length = len(response)
        generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Generate and store embedding
        embedding_vec = self.embedding_service.generate_embedding(
            f"{response}, {user_input}"
        )
        embedding_json = json.dumps(embedding_vec)
        
        # Save to database
        self.repo.add_chat_message(
            chat_id, user_input, response, embedding_json,
            config['model_type'], config['language_model'],
            response_length, execution_time, generated_at
        )
        
        return {
            "response": response,
            "chat_id": chat_id,
            "response_metadata": {
                "response_length": response_length,
                "execution_time": execution_time,
                "generated_at": generated_at,
                "web_search_enabled": web_search_enabled,
                "source_urls": source_urls if web_search_enabled else []
            }
        }
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters for most models)"""
        return len(text) // 4
    
    def _get_total_context_tokens(self, formatted_history: List[Tuple[str, str]], 
                                user_input: str, prompt_template: str) -> int:
        """Estimate total tokens that will be sent to the model"""
        history_text = "\n".join([f"User: {h[0]}\nAssistant: {h[1]}" for h in formatted_history])
        full_prompt = prompt_template.format(chat_history=history_text, question=user_input)
        return self._estimate_tokens(full_prompt)


# Singleton instance
chat_service = ChatService()
