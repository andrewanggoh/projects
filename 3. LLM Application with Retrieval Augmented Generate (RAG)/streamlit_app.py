# Libraries
import streamlit as st
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from openai import OpenAI

# ----------------- Backend RAG & LLM -----------------

## Sentence Transformer Model
@st.cache_resource
def load_model():
    return SentenceTransformer('paraphrase-MiniLM-L6-v2')

model = load_model()

## FAISS & Cosine
def build_faiss_index_cosine(data):
    # Embedding
    embedding = model.encode(data, convert_to_numpy=True)

    # Calculate for cosine similarity
    embedding = embedding / np.linalg.norm(embedding, axis=1, keepdims=True)
    embedding = embedding.astype('float32')  # FAISS hanya menerima float32

    # FAISS Indexing
    dim = embedding.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embedding)

    return index, embedding

## Retrieval
def retrieve(query, index, df, top_k=None):
    return df  

## LLM - Generate Answer
def generate_answer(query, context, key):
    # API Client Setup
    client = OpenAI(
        api_key= key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    # Sets the LLM's behavior
    system_message = "You are an intelligent assistant who answers questions based on the provided data."

    # Combines the user's query and retrieved context into a structured prompt
    user_message = f"""
    Question: {query}

    Relevant data:
    {context}
    """
    # Requesting response from LLM
    response = client.chat.completions.create(
        # Gemini model
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
    )

    return response.choices[0].message.content

def transform_data(df, selected_columns):
    df["text"] = df[selected_columns].astype(str).agg(" | ".join, axis=1)
    return df   

# ----------------- UI -----------------

## Title Main Page
st.markdown(
    """
    <div style='text-align: center;'>
        <h1>🤖 LLM-RAG Chatbot</h1>
        <p>Developed by Andrew Oksner Anggoh | Powered by Gemini 2.0 Flash</p>
    </div>
    """,
    unsafe_allow_html=True
)

## Sidebar
### Input Sidebar
st.sidebar.markdown(
    "<h2 style='text-align: center;'>Settings</h2>",
    unsafe_allow_html=True
)

uploaded_file = st.sidebar.file_uploader("Upload File", type = 'csv')
input_api_key = st.sidebar.text_input("Input API Key", type = 'password')
button_api = st.sidebar.button('Activate API Key')

## Sidebar Backend Setting
if 'api_key' not in st.session_state:
    st.session_state.api_key = None

if input_api_key and button_api:
    st.session_state.api_key = input_api_key
    st.sidebar.success("API Key Active")

## Main Input
### Output when CSV file isn't uploaded yet
if uploaded_file == None:
        st.warning("📂 Please upload the CSV file first.")

### Output when CSV file is uploaded
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df = df.astype(str)
    st.subheader("Choose Column(s)")
    selected_columns = st.multiselect(
        label = "Choose Column(s) to Analyze:",
        options = df.columns.to_list(),
        default = df.columns.to_list()
    )

    if not selected_columns:
        st.warning("⚠️ Please choose at least one column.")
        st.stop()

    ### Preview of chosen column(s)
    st.dataframe(df[selected_columns])

    ### Question box will appear once you've selected a column.
    query = st.text_input("Input Your Question")
    run_query = st.button("Answer")

    ### Run All Processes
    if run_query and st.session_state.api_key:
        try:
            df = transform_data(df, selected_columns)
            index, _ = build_faiss_index_cosine(df['text'].to_list())

            with st.spinner("Finding Matching Information"):
                results = retrieve(query, index, df)
                context = "\n".join(results["text"].to_list())

            with st.spinner("Generating Answers"):
                answer = generate_answer(query, context, st.session_state.api_key)

            st.subheader("💬 Answer:")
            st.success(answer)
        except Exception as e:
            st.error(f"Error: {str(e)}")
    elif run_query and not st.session_state.api_key:
        st.warning("🔐 You must input and activate the API Key first.")
