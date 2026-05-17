import os

import streamlit as st

from main import main_logic

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

st.title("Personal Assistant for answering your questions.")

uploaded_files = st.file_uploader(
    "Upload documents",
    type=["pdf", "txt", "docx"],
    accept_multiple_files=True,
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        destination = os.path.join(DATA_DIR, uploaded_file.name)
        with open(destination, "wb") as file_handle:
            file_handle.write(uploaded_file.getbuffer())

    st.success(f"Saved {len(uploaded_files)} file(s) to the data directory.")

question = st.text_input("Ask a question about your uploaded documents")

if st.button("Submit") and question:
    with st.spinner("Generating response..."):
        answer = main_logic(question)

    st.write(answer or "No answer could be generated.")
