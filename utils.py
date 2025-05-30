from langchain_huggingface import HuggingFaceEmbeddings
from config import EMBEDDING_MODEL_NAME, GROQ_API_KEY, LLM_MODEL_NAME
import os
import re
import ollama
from groq import Groq
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS, Chroma
# from embeddings import get_embedding_model
from langchain_groq import ChatGroq
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.question_answering import load_qa_chain
from langchain.chains import LLMChain
from langchain.chains.conversational_retrieval.prompts import CONDENSE_QUESTION_PROMPT
from langchain_community.chat_models import ChatOllama
from langchain.docstore.document import Document
from langchain_community.document_loaders import UnstructuredURLLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
        
def get_embedding():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
def generate_embedding(text):
    embedding_model = get_embedding()
    return embedding_model.embed_query(text)  # or embed_documents([text]) if needed

# FAISS_INDEX_PATH = "faiss_index"
def create_vectordb(documents, model_name, chunk_size, faiss_index_path):
    FAISS_INDEX_PATH = "vectorDB/"+faiss_index_path
    
    embedding_model = get_embedding()
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
            print(docs)
            all_documents.extend(docs)
        
        except Exception as e:
            print(f"Failed to load {doc_type}: {path} with error: {e}")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=50)
    chunked_texts = [chunk for doc in all_documents for chunk in text_splitter.split_text(doc.page_content)]

    
    if model_name == "faiss":
        print("Creating FAISS vector store...")
        vectorstore = FAISS.from_texts(chunked_texts, embedding_model)
        vectorstore.save_local(FAISS_INDEX_PATH)
    
    elif model_name == "chroma":
        print("Creating Chroma vector store...")
        vectorstore = Chroma.from_texts(
            texts=chunked_texts,
            embedding=embedding_model,
            persist_directory=FAISS_INDEX_PATH
        )
        vectorstore.persist()
    
    else:
        raise ValueError(f"Unsupported vector store type: {model_name}")
    
    return vectorstore

def get_or_create_faiss_index(faiss_index_path):
    FAISS_INDEX_PATH = "vectorDB/"+faiss_index_path
    # print(FAISS_INDEX_PATH)
    embedding_model = get_embedding()

    if os.path.exists(FAISS_INDEX_PATH):
        # Load FAISS index if it exists
        vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embedding_model, allow_dangerous_deserialization=True)
    else:
        # Create a new FAISS index if it doesn't exist
        from langchain_community.document_loaders import UnstructuredURLLoader
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        # Sample URLs
        urls = [
            "https://google.github.io/styleguide/docguide/style.html",
            "https://www.markdownguide.org/basic-syntax/",
            "https://gist.github.com/rt2zz/e0a1d6ab2682d2c47746950b84c0b6ee",
            "https://gist.github.com/allysonsilva/85fff14a22bbdf55485be947566cc09e",
            "https://israelmitolu.hashnode.dev/markdown-for-technical-writers-tips-tricks-and-best-practices"
        ]
        # urls = [
        #     "https://thebarista.co.uk/blog/the-best-way-to-make-coffee-at-home",
        #     "https://food52.com/blog/26964-how-to-make-coffee?srsltid=AfmBOoqD6NA03WxwYtrfl_At3DsGM4tkuY-l6cqEERq5UW4FSBtHqBRb",
        #     "https://www.vegrecipesofindia.com/hot-coffee-recipe-cafe-style/",
        #     "https://www.yummytummyaarthi.com/how-to-make-perfect-cup-of-instant/"
        # ]
        loader = UnstructuredURLLoader(urls=urls)
        documents = loader.load()
        
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunked_texts = [chunk for doc in documents for chunk in text_splitter.split_text(doc.page_content)]
        
        # Create FAISS index and save it
        vectorstore = FAISS.from_texts(chunked_texts, embedding_model)
        vectorstore.save_local(FAISS_INDEX_PATH)
    
    return vectorstore

def get_llm(model_name, api_key, model_type):
    if model_type == "GROQ":
        return ChatGroq(
            model_name=model_name,
            temperature=0.4,
            groq_api_key=api_key
        )
    elif model_type == "Ollama":
        return  ChatOllama(
            model=model_name, 
            temperature=0.4
        )

def get_retrieval_chain(prompt_template, faiss_index_path = "faiss_index", model_name=LLM_MODEL_NAME, api_key = GROQ_API_KEY, model_type="GROQ"):
    vectorstore = get_or_create_faiss_index(faiss_index_path)
    retriever = vectorstore.as_retriever()
    
    llm = get_llm(model_name, api_key, model_type)
    # print(llm)
    # print(llm.invoke("hellow"))
    
    prompt_template = prompt_template
    # print(prompt_template)
    combine_docs_chain = load_qa_chain(llm, chain_type="stuff", prompt=prompt_template)
    question_generator = LLMChain(llm=llm, prompt=CONDENSE_QUESTION_PROMPT)
    print("Question generator could be found")
    # Define ConversationalRetrievalChain
    retrieval_qa_chain = ConversationalRetrievalChain(
        retriever=retriever,
        combine_docs_chain=combine_docs_chain,
        question_generator=question_generator,
        return_source_documents=True
    )
    print("Retrieval QA chain could be found", retrieval_qa_chain)
    return retrieval_qa_chain

def prompt_generator_groq(model_type, model_name, app_purpose, doc_detail, api_key = ""):
    content = (
                    "You are an AI assistant that helps generate optimized prompt templates for custom RAG (Retrieval-Augmented Generation) applications. "
                    "The user is building a RAG-based assistant by uploading their own documentation and describing the purpose of their app. Your job is to analyze the user’s stated purpose and the description of the uploaded documents, and generate a reusable prompt template that best aligns with their goals. "
                    "Your generated prompt should guide an LLM to provide accurate, relevant, and specific answers based solely on the user’s documents.\n\n"
                    "Focus on:"
                    "- Capturing the **intent and purpose** of the RAG assistant"
                    "- Reflecting how the documentation is described (e.g., style, domain, complexity)"
                    "- Encouraging responses grounded strictly in the uploaded documents"
                    "- Producing a clear, concise, and effective instruction format that can be reused to answer user questions"
                   " Avoid:"
                    "- Including any direct content from the documentation"
                    "- Over-explaining or adding generic LLM instructions"
                    "- Making assumptions outside the user’s described purpose or documents"
                    "Your output should be:"
                    "- A single user-facing prompt instruction"
                    "- Focused, role-specific, and aligned with the RAG application’s intended use"
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
    if model_type == "GROQ":
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": content
                },
                {
                    "role": "user",
                    "content": f"write a prompt template for RAG Application good fit for this purpose:{app_purpose}, and it's documentation detials : {doc_detail}"
                }
            ],
            model=model_name,
            temperature=0.3, 
            top_p=1,
            stop=None,
            stream=False,
        )
        res = chat_completion.choices[0].message.content.strip()
        match = re.search(r"</think>\s*(.*)", res, re.DOTALL)
        if match:
            after_think = match.group(1).strip()
            return after_think
        else:
            return res
    elif model_type == "Ollama":
        chat_completion = ollama.chat(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": content
            },
            {
                "role": "user",
                "content": f"write a prompt template for RAG Application good fit for this purpose: {app_purpose}, and it's documentation details: {doc_detail}"
            }
        ]
        )
        res = chat_completion['message']['content'].strip()
        match = re.search(r"</think>\s*(.*)", res, re.DOTALL)
        if match:
            after_think = match.group(1).strip()
            return after_think
        else:
            return res


def name_generator(model_type, model_name, first_prompt, api_key = ""):
    content = (
        "You are an AI assistant that helps generate short name for the season chat"
        "The user is building a RAG-based assistant by uploading their own documentation and describing the purpose of their app. Your job is to analyze the user’s first prompt request and give a meaningful name for it's chat season"
        "Your generated name should be meaningful and short at least 4 words"
        """
            **OUTPUT** : Only write a short name (at least 4 words)
        """
    )   
    if model_type == "GROQ":
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": content
                },
                {
                    "role": "user",
                    "content": f"suggest meaningful name for chat season regarding this first prompt request that user wrote :{first_prompt}, in at least 4 words"
                }
            ],
            model=model_name,
            temperature=0.3, 
            top_p=1,
            stop=None,
            stream=False,
        )
        res = chat_completion.choices[0].message.content.strip()
        match = re.search(r"</think>(.*)", res, re.DOTALL)
        if match:
            after_think = match.group(1)
            return after_think
        else:
            return res
    elif model_type == "Ollama":
        chat_completion = ollama.chat(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": content
            },
            {
                "role": "user",
                "content": f"suggest meaningful name for chat season regarding this first prompt request that user wrote :{first_prompt}, in at least 4 words"
            }
        ]
        )
        res = chat_completion['message']['content'].strip()
        match = re.search(r"</think>(.*)", res, re.DOTALL)
        if match:
            after_think = match.group(1)
            return after_think
        else:
            return res