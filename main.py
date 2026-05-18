import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

from dotenv import find_dotenv, load_dotenv

try:
    from langchain_community.document_loaders import (
        PyPDFLoader,
        TextLoader,
        UnstructuredWordDocumentLoader,
    )
    from langchain_community.vectorstores import FAISS
    from langchain_google_genai import (
        ChatGoogleGenerativeAI,
        GoogleGenerativeAIEmbeddings,
    )
except ImportError:
    PyPDFLoader = cast(Any, None)
    TextLoader = cast(Any, None)
    UnstructuredWordDocumentLoader = cast(Any, None)
    FAISS = cast(Any, None)
    ChatGoogleGenerativeAI = cast(Any, None)  # type: ignore[misc]
    GoogleGenerativeAIEmbeddings = cast(Any, None)  # type: ignore[misc]

load_dotenv(find_dotenv())

DATA_DIR = "data"
INDEX_BASE_DIR = "indexes"
SUPPORTED_FILE_TYPES = {"pdf", "txt", "docx"}


def _require_dependency(dependency, package_name):
    if dependency is None:
        raise ImportError(
            f"Missing optional dependency '{package_name}'. Install project requirements first."
        )
    return dependency


def get_gemini_embeddings():
    embeddings_class = _require_dependency(
        GoogleGenerativeAIEmbeddings,
        "langchain-google-genai",
    )
    return embeddings_class(
        model="models/text-embedding-004",
        verbose=True,
    )


def get_gemini_llm():
    llm_class = _require_dependency(
        ChatGoogleGenerativeAI,
        "langchain-google-genai",
    )
    return llm_class(
        model="gemini-1.5-flash",
        temperature=0.2,
        verbose=True,
    )


def load_docs(file_type, file_paths):
    pdf_loader = _require_dependency(PyPDFLoader, "langchain-community")
    text_loader = _require_dependency(TextLoader, "langchain-community")
    docx_loader = _require_dependency(
        UnstructuredWordDocumentLoader,
        "langchain-community",
    )
    docs = []
    for file_path in file_paths:
        if file_type == "pdf":
            docs.extend(pdf_loader(str(file_path)).load())
        elif file_type == "txt":
            docs.extend(text_loader(str(file_path)).load())
        elif file_type == "docx":
            docs.extend(docx_loader(str(file_path)).load())
    return docs


def build_or_load_faiss(file_type, file_paths):
    faiss_class = _require_dependency(FAISS, "langchain-community")
    embeddings = get_gemini_embeddings()
    index_dir = os.path.join(INDEX_BASE_DIR, f"{file_type}_index")
    meta_path = os.path.join(INDEX_BASE_DIR, f"{file_type}_indexed.json")

    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r") as f:
                indexed_files = set(json.load(f))
        except json.JSONDecodeError:
            indexed_files = set()
    else:
        indexed_files = set()

    current_files = set(str(Path(path).resolve()) for path in file_paths)
    new_files = current_files - indexed_files

    faiss_index = None
    index_exists = os.path.exists(index_dir)

    if index_exists:
        faiss_index = faiss_class.load_local(
            index_dir,
            embeddings,
            allow_dangerous_deserialization=True,
        )

    if new_files:
        print(f"Found {len(new_files)} new file(s) for '{file_type}'. Indexing....")
        docs = load_docs(file_type, list(new_files))
        if docs:
            if faiss_index:
                faiss_index.add_documents(docs)
            else:
                faiss_index = faiss_class.from_documents(docs, embeddings)

            faiss_index.save_local(index_dir)

            with open(meta_path, "w") as f:
                json.dump(sorted(current_files), f, indent=2)
    elif faiss_index is not None:
        print(f"FAISS index exists for '{file_type}'.")
    else:
        print(f"No index found for '{file_type}' and no documents were indexed.")

    return faiss_index


def retrieve_all_sources(query, stores, k=2):
    all_docs = []
    for store in stores.values():
        if store is None:
            continue
        all_docs.extend(store.similarity_search(query, k=k))
    return all_docs


def scan_data_directory():
    file_map = defaultdict(list)
    for path in Path(DATA_DIR).glob("*"):
        ext = path.suffix.lower()[1:]
        if ext not in SUPPORTED_FILE_TYPES:
            continue
        file_map[ext].append(path)
    return file_map


def main_logic(query):
    os.makedirs(INDEX_BASE_DIR, exist_ok=True)

    file_groups = scan_data_directory()

    stores = {
        file_type: build_or_load_faiss(file_type, file_paths)
        for file_type, file_paths in file_groups.items()
    }
    stores = {file_type: store for file_type, store in stores.items() if store is not None}

    if not stores:
        print("No supported files found in 'data/' folder.")
        return

    context_docs = retrieve_all_sources(query, stores)
    context_text = "\n".join([doc.page_content for doc in context_docs])

    llm = get_gemini_llm()
    response = llm.invoke(
        f"Answer the following based on the context:\n{context_text}\n\nQuestion: {query}"
    )
    return response.content


if __name__ == "__main__":
    question = input("Ask your question: ")
    print(main_logic(question))
