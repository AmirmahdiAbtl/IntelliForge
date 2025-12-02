"""Prompt generation service for RAG applications"""
import re
import ollama
from groq import Groq


class PromptGenerationService:
    """Service for generating RAG prompts using LLMs"""
    
    def generate_prompt(self, model_type: str, model_name: str, app_purpose: str, 
                       doc_details: str, api_key: str = "") -> str:
        """Generate optimized prompt template for RAG application"""
        
        system_content = (
            "You are an AI assistant that helps generate optimized prompt templates for custom RAG (Retrieval-Augmented Generation) applications. "
            "The user is building a RAG-based assistant by uploading their own documentation and describing the purpose of their app. Your job is to analyze the user's stated purpose and the description of the uploaded documents, and generate a reusable prompt template that best aligns with their goals. "
            "Your generated prompt should guide an LLM to provide accurate, relevant, and specific answers based solely on the user's documents.\n\n"
            "Focus on:"
            "- Capturing the **intent and purpose** of the RAG assistant"
            "- Reflecting how the documentation is described (e.g., style, domain, complexity)"
            "- Encouraging responses grounded strictly in the uploaded documents"
            "- Producing a clear, concise, and effective instruction format that can be reused to answer user questions"
            " Avoid:"
            "- Including any direct content from the documentation"
            "- Over-explaining or adding generic LLM instructions"
            "- Making assumptions outside the user's described purpose or documents"
            "Your output should be:"
            "- A single user-facing prompt instruction"
            "- Focused, role-specific, and aligned with the RAG application's intended use"
            "Example output format:"
            """
            You are a helpful AI assistant that answers strictly based on the provided documentation. Your job is to help the user understand the content and generate helpful responses. Here's how you should respond:
                
                - If the user asks about information in the documentation, provide a clear answer based on the material.
                - If the user asks for examples, generate helpful examples based on the documentation.
                - If the user asks a question that is answered in the documentation or in our previous chat history, respond directly and accurately.
                - If the answer can be reasonably inferred, provide a general response grounded in the documentation.
                - If the topic is completely unrelated to the documentation, respond with:
                *\"I couldn't find that in the provided documentation.\"*
                
            **OUTPUT** : Only write template nothing more even one word
            """
        )
        
        user_message = f"write a prompt template for RAG Application good fit for this purpose: {app_purpose}, and it's documentation details: {doc_details}"
        
        if model_type == "GROQ":
            return self._generate_with_groq(system_content, user_message, model_name, api_key)
        elif model_type == "Ollama":
            return self._generate_with_ollama(system_content, user_message, model_name)
        elif model_type == "GitHub":
            # For GitHub models, use the default prompt since we don't have GitHub API integration yet
            return self._get_default_prompt(app_purpose, doc_details)
        else:
            # Default fallback prompt
            return self._get_default_prompt(app_purpose, doc_details)
    
    def _generate_with_groq(self, system_content: str, user_message: str, 
                           model_name: str, api_key: str) -> str:
        """Generate prompt using Groq API"""
        try:
            client = Groq(api_key=api_key)
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_message}
                ],
                model=model_name,
                temperature=0.3,
                top_p=1,
                stop=None,
                stream=False,
            )
            
            res = chat_completion.choices[0].message.content.strip()
            return self._clean_response(res)
            
        except Exception as e:
            print(f"Error generating prompt with Groq: {e}")
            return self._get_default_prompt()
    
    def _generate_with_ollama(self, system_content: str, user_message: str, 
                             model_name: str) -> str:
        """Generate prompt using Ollama"""
        try:
            chat_completion = ollama.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_message}
                ]
            )
            
            res = chat_completion['message']['content'].strip()
            return self._clean_response(res)
            
        except Exception as e:
            print(f"Error generating prompt with Ollama: {e}")
            return self._get_default_prompt()
    
    def _clean_response(self, response: str) -> str:
        """Clean the response to extract only the prompt template"""
        # Remove thinking tags if present
        match = re.search(r"</think>\s*(.*)", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response
    
    def _get_default_prompt(self, app_purpose: str = "", doc_details: str = "") -> str:
        """Return default prompt template with context"""
        base_prompt = """You are a helpful AI assistant that answers questions based on the provided documentation."""
        
        if app_purpose and app_purpose != "A general purpose AI assistant":
            base_prompt += f" Your purpose is to help with: {app_purpose}."
        
        if doc_details:
            base_prompt += f" The documentation covers: {doc_details}."
        
        base_prompt += """
            Guidelines:
            - Provide clear, accurate answers based on the documentation
            - If information is not in the documentation, say "I couldn't find that information in the provided documentation"
            - Stay focused on the content and purpose of the uploaded materials
            - Provide helpful examples when appropriate
            """
        
        return base_prompt


# Create service instance
prompt_generation_service = PromptGenerationService()