from __future__ import annotations

import os

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


st.set_page_config(page_title="Vietnamese RAG Assistant", layout="wide")
st.title("Vietnamese Internal Docs QA Assistant")

with st.sidebar:
    st.header("Settings")
    top_k = st.slider("top_k", min_value=1, max_value=20, value=5)
    department_filter = st.selectbox("Department", ["", "HR", "Engineering", "Security", "General"])
    access_level = st.selectbox("Access Level", ["public", "internal", "restricted"])
    debug = st.checkbox("Debug mode", value=True)

question = st.text_area("Ask a question", placeholder="Example: Chinh sach nghi phep hang nam cua cong ty la gi?")

if st.button("Ask"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        payload = {
            "question": question,
            "top_k": top_k,
            "department_filter": department_filter or None,
            "access_level": access_level,
            "debug": debug,
        }
        resp = requests.post(f"{API_BASE_URL}/ask", json=payload, timeout=60)
        if resp.status_code != 200:
            st.error(f"Request failed: {resp.status_code} - {resp.text}")
        else:
            data = resp.json()
            st.subheader("Answer")
            st.write(data["answer"])

            c1, c2 = st.columns(2)
            with c1:
                st.metric("Confidence", data["confidence"])
            with c2:
                st.metric("Status", data["status"])

            st.subheader("Citations")
            if data["citations"]:
                for c in data["citations"]:
                    st.markdown(f"- `{c.get('chunk_id', '')}` | {c.get('title', '')} | {c.get('section_path', '')}")
            else:
                st.info("No citations returned.")

            if data.get("clarifying_question"):
                st.warning(data["clarifying_question"])

            if debug and data.get("debug"):
                st.subheader("Debug")
                st.json(data["debug"])

st.divider()
st.subheader("Search only")
search_query = st.text_input("Search query")
if st.button("Search"):
    if search_query.strip():
        payload = {
            "query": search_query,
            "top_k": top_k,
            "department_filter": department_filter or None,
            "access_level": access_level,
            "debug": debug,
        }
        resp = requests.post(f"{API_BASE_URL}/search", json=payload, timeout=60)
        if resp.status_code != 200:
            st.error(f"Search failed: {resp.status_code} - {resp.text}")
        else:
            data = resp.json()
            st.json(data)
