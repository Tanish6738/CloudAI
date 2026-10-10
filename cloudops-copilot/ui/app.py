"""Streamlit UI for CloudOps Copilot."""

import uuid
import httpx
import streamlit as st

# Page config
st.set_page_config(
    page_title="CloudOps Copilot",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 CloudOps Copilot")
st.markdown("Ask questions about your AWS logs. Powered by RAG + Bedrock.")

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# API endpoint
API_URL = "http://localhost:8000"

# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("cited_log_ids"):
            with st.expander("📋 Citations"):
                st.code("\n".join(message["cited_log_ids"]))

# Chat input
if prompt := st.chat_input("Ask a question about your logs..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Call API
    with st.spinner("Searching logs and generating answer..."):
        try:
            response = httpx.post(
                f"{API_URL}/chat",
                json={
                    "session_id": st.session_state.session_id,
                    "question": prompt,
                },
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            answer = data.get("answer", "No answer returned.")
            cited_log_ids = data.get("cited_log_ids", [])
            warning = data.get("warning")

            # Add assistant message to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "cited_log_ids": cited_log_ids,
            })

            # Display response
            with st.chat_message("assistant"):
                st.markdown(answer)

                if cited_log_ids:
                    with st.expander("📋 Citations"):
                        st.code("\n".join(cited_log_ids))

                if warning:
                    st.warning(f"⚠️ {warning}")

        except httpx.HTTPError as e:
            st.error(f"API Error: {e}")
        except Exception as e:
            st.error(f"Error: {e}")

# Sidebar
with st.sidebar:
    st.markdown("### Session Info")
    st.code(st.session_state.session_id, language="text")

    st.markdown("### About")
    st.markdown("""
    CloudOps Copilot answers questions about AWS logs using:
    - **Bedrock Nova Lite** for answer generation
    - **Bedrock Titan Embeddings v2** for semantic search
    - **FAISS** for efficient similarity search
    
    Built with ❤️ using Python, FastAPI, and Streamlit.
    """)
