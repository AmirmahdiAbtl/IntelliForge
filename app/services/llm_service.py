"""LLM service for language model operations"""
import ollama
from groq import Groq
from openai import OpenAI
from langchain_groq import ChatGroq
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import LLMChain, ConversationalRetrievalChain
from langchain_classic.chains.question_answering import load_qa_chain
from langchain_classic.chains.conversational_retrieval.prompts import CONDENSE_QUESTION_PROMPT
from app.config import config
from app.services.retriever_service import create_reranking_retriever


class LLMService:
    """Handle LLM operations"""
    
    @staticmethod
    def get_llm(model_name: str, api_key: str, model_type: str):
        """
        Get LLM instance based on model type
        
        Args:
            model_name: Name of the model
            api_key: API key (if needed)
            model_type: 'ChatGPT', 'Ollama', 'GROQ', or 'GitHub'
        """
        if model_type == "GROQ":
            return ChatGroq(
                groq_api_key=api_key or config.GROQ_API_KEY,
                model_name=model_name
            )
        elif model_type == "Ollama":
            return ChatOllama(model=model_name)
        elif model_type == "GitHub":
            return ChatOpenAI(
                base_url="https://models.github.ai/inference",
                api_key=api_key or config.GITHUB_TOKEN,
                model=model_name
            )
        elif model_type == "ChatGPT":
            # You would add OpenAI implementation here
            raise NotImplementedError("ChatGPT integration not yet implemented")
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    @staticmethod
    def create_chat_chain(llm, prompt_template: str, 
                         input_variables: list) -> LLMChain:
        """Create a simple chat chain"""
        prompt = PromptTemplate(
            input_variables=input_variables,
            template=prompt_template
        )
        return LLMChain(llm=llm, prompt=prompt)
    
    @staticmethod
    def create_retrieval_chain(llm, vectorstore, prompt_template=None, 
                             use_reranking=True, top_k_retrieval=None, 
                             top_k_reranked=None):
        """Create a conversational retrieval chain with custom prompt and reranking"""
        question_generator = LLMChain(llm=llm, prompt=CONDENSE_QUESTION_PROMPT)
        
        # Use custom prompt template if provided, otherwise use default with documentation constraint
        if prompt_template:
            # Create a custom QA prompt that includes the user's prompt template
            qa_prompt_template = f"""{prompt_template}

            Context from documentation:
            {{context}}

            Question: {{question}}

            Please answer the question based ONLY on the provided documentation context. If the information is not available in the context, respond with "I couldn't find that information in the provided documentation."

            Answer:"""
        else:
            # Default strict RAG prompt
            qa_prompt_template = """You are a helpful AI assistant that answers questions based ONLY on the provided documentation context.

                Context from documentation:
                {context}

                Question: {question}

                Guidelines:
                - Answer ONLY based on the provided documentation context
                - If the information is not available in the context, respond with "I couldn't find that information in the provided documentation"
                - Do not use your general knowledge to answer questions
                - Be precise and cite specific parts of the documentation when possible
                - The provided context has been carefully selected and reranked for relevance to your question

                Answer:"""

        # Create custom prompt
        from langchain_core.prompts import PromptTemplate
        qa_prompt = PromptTemplate(
            template=qa_prompt_template,
            input_variables=["context", "question"]
        )
        
        # Create document chain with custom prompt
        doc_chain = load_qa_chain(llm, chain_type="stuff", prompt=qa_prompt)
        
        # Create retriever with reranking capabilities
        if use_reranking:
            retriever = create_reranking_retriever(
                vectorstore=vectorstore,
                top_k_retrieval=top_k_retrieval,
                top_k_reranked=top_k_reranked,
                enable_reranking=True
            )
        else:
            retriever = vectorstore.as_retriever()
        
        return ConversationalRetrievalChain(
            retriever=retriever,
            question_generator=question_generator,
            combine_docs_chain=doc_chain,
            return_source_documents=True
        )
    
    @staticmethod
    def generate_name(model_type: str, model_name: str, 
                     prompt: str, api_key: str = None) -> str:
        """Generate a name for a chat using LLM"""
        try:
            if model_type == "GROQ":
                client = Groq(api_key=api_key or config.GROQ_API_KEY)
                completion = client.chat.completions.create(
                    model=model_name,
                    messages=[{
                        "role": "user",
                        "content": f"Generate a short, concise name (max 5 words) for a conversation that starts with: '{prompt[:100]}'"
                    }],
                    temperature=0.7,
                    max_tokens=20
                )
                return completion.choices[0].message.content.strip()
            elif model_type == "GitHub":
                client = OpenAI(
                    base_url="https://models.github.ai/inference",
                    api_key=api_key or config.GITHUB_TOKEN
                )
                completion = client.chat.completions.create(
                    model=model_name,
                    messages=[{
                        "role": "user",
                        "content": f"Generate a short, concise name (max 5 words) for a conversation that starts with: '{prompt[:100]}'"
                    }],
                    temperature=0.7,
                    max_tokens=20
                )
                return completion.choices[0].message.content.strip()
            elif model_type == "Ollama":
                response = ollama.chat(
                    model=model_name,
                    messages=[{
                        'role': 'user',
                        'content': f"Generate a short, concise name (max 5 words) for a conversation that starts with: '{prompt[:100]}'"
                    }]
                )
                return response['message']['content'].strip()
            else:
                return prompt[:50] if len(prompt) > 50 else prompt
        except Exception as e:
            print(f"Error generating name: {e}")
            return prompt[:50] if len(prompt) > 50 else prompt


# Singleton instance
llm_service = LLMService()
