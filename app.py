import os
import numpy as np
import gradio as gr
from groq import Groq
from sentence_transformers import SentenceTransformer

# ----------------------------------
# Groq API
# ----------------------------------
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Add GROQ_API_KEY in HuggingFace Secrets")

client = Groq(api_key=GROQ_API_KEY)

# ----------------------------------
# Embeddings
# ----------------------------------
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# ----------------------------------
# Load document
# ----------------------------------
with open("document.txt", "r", encoding="utf-8") as f:
    document_text = f.read()

# ----------------------------------
# Chunking
# ----------------------------------
def chunk_text(text, size=300):
    words = text.split()
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size)]

chunks = chunk_text(document_text)

# ----------------------------------
# Precompute embeddings
# ----------------------------------
chunk_embeddings = embedder.encode(chunks, convert_to_numpy=True)
chunk_embeddings /= np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)

# ----------------------------------
# Retrieval
# ----------------------------------
def retrieve(query, top_k=3):
    q_emb = embedder.encode([query], convert_to_numpy=True)
    q_emb /= np.linalg.norm(q_emb, axis=1, keepdims=True)
    scores = chunk_embeddings @ q_emb.T
    ids = np.argsort(-scores.squeeze())[:top_k]
    return [chunks[i] for i in ids if scores[i] > 0]

# ----------------------------------
# Chat Function (Gradio 6+ Compatible)
# ----------------------------------
def chat(user_message, history):
    history = history or []

    if not user_message.strip():
        return history, history, ""

    context = "\n\n".join(retrieve(user_message))

    if not context:
        reply = "Sorry, this information is not available in my data."
    else:
        system_prompt = f"""
You are MujahidGPT — the official AI assistant of JHK Solution.
Rules:
- Answer ONLY using the provided context.
- If info is missing, reply exactly:
"Sorry, this information is not available in my data."
Context:
{context}
"""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.1
        )

        reply = response.choices[0].message.content.strip()

    # ✅ Append in NEW message format
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})

    return history, history, ""

# ----------------------------------
# Gradio UI
# ----------------------------------
with gr.Blocks() as demo:
    gr.Markdown("""
# 🤖 MujahidGPT  
### JHK Solution Personal Assistant  
**Final Year Project (DIT)**  
**By:** Mujahid Hussain  
**Supervisor:** Mr. Muzamail ur Rehman  
---
Ask anything about **JHK Solution**
""")

    chatbot = gr.Chatbot(height=500)
    user_input = gr.Textbox(
        label="Ask your question",
        placeholder="Type your question here..."
    )
    state = gr.State([])

    user_input.submit(
        chat,
        inputs=[user_input, state],
        outputs=[chatbot, state, user_input]
    )

    gr.Button("Clear Chat").click(
        lambda: ([], [], ""),
        outputs=[chatbot, state, user_input]
    )

# ----------------------------------
# Launch
# ----------------------------------
if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
