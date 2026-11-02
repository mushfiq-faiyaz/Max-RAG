import os
import re
import sys
import pdfplumber
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path

DOCS_DIR = "docs"
DB_DIR = "chroma_db"
COLLECTION_NAME = "client_knowledge"
EMBED_MODEL = "all-MiniLM-L6-v2"

def format_table_to_markdown(table_data):
    if not table_data: return ""
    clean_table = []
    for row in table_data:
        clean_row = []
        for cell in row:
            if cell is None: clean_row.append("")
            else:
                c_str = " ".join(str(cell).replace("\n", " ").split())
                if c_str in ("—", "", "-", "N/A"): c_str = "None"
                clean_row.append(c_str)
        clean_table.append(clean_row)
    
    if not clean_table or not any(clean_table): return ""

    col_count = max(len(r) for r in clean_table)
    for r in clean_table:
        while len(r) < col_count: r.append("")

    col_widths = [max(len(r[c]) for r in clean_table) for c in range(col_count)]
    lines = []
    header = "| " + " | ".join(clean_table[0][c].ljust(col_widths[c]) for c in range(col_count)) + " |"
    sep = "| " + " | ".join("-" * max(3, col_widths[c]) for c in range(col_count)) + " |"
    lines.append(header)
    lines.append(sep)
    for row in clean_table[1:]:
        lines.append("| " + " | ".join(row[c].ljust(col_widths[c]) for c in range(col_count)) + " |")

    return f"\n\n[TABLE EXTRACTED]\n{chr(10).join(lines)}\n\n"

def extract_page_text_with_tables(page):
    tables = page.find_tables()
    if not tables: return page.extract_text() or ""

    sorted_tables = sorted(tables, key=lambda t: t.bbox[1])
    parts, last_bottom = [], 0

    for t in sorted_tables:
        bbox = t.bbox
        if bbox[1] > last_bottom:
            above_crop = page.crop((0, last_bottom, page.width, bbox[1]))
            above_text = above_crop.extract_text()
            if above_text and above_text.strip(): parts.append(above_text.strip())

        t_data = t.extract()
        formatted_t = format_table_to_markdown(t_data)
        if formatted_t.strip(): parts.append(formatted_t.strip())
        last_bottom = max(last_bottom, bbox[3])

    if last_bottom < page.height:
        below_crop = page.crop((0, last_bottom, page.width, page.height))
        below_text = below_crop.extract_text()
        if below_text and below_text.strip(): parts.append(below_text.strip())

    return "\n\n".join(parts)

def chunk_text(text, max_chars=1000, overlap=200):
    # PROTECT TABLES: If it's a table, keep it as one giant chunk.
    if "[TABLE EXTRACTED]" in text and text.strip().startswith("[TABLE EXTRACTED]"):
        return [text]

    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + max_chars
        if end >= text_len:
            chunks.append(text[start:].strip())
            break
            
        chunk = text[start:end]
        last_nl = chunk.rfind('\n')
        last_space = chunk.rfind(' ')
        
        # Try to cut at a natural sentence boundary
        if last_nl > start + (max_chars // 2):
            end = start + last_nl
        elif last_space > start + (max_chars // 2):
            end = start + last_space
            
        chunks.append(text[start:end].strip())
        start = end - overlap # THE OVERLAP FIX
        
    return [c for c in chunks if len(c) > 20]

def build_knowledge_base():
    print("1. Reading files in /docs using pdfplumber...")
    documents, metadatas, ids = [], [], []
    chunk_id = 0

    if not os.path.exists(DOCS_DIR):
        print(f"❌ Error: '{DOCS_DIR}' folder does not exist.")
        return

    files = [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf') or f.endswith('.txt')]
    if not files:
        print("❌ No files found. Aborting.")
        return

    for filename in files:
        print(f"   📄 Reading {filename}...")
        full_text = ""
        try:
            if filename.endswith('.pdf'):
                with pdfplumber.open(os.path.join(DOCS_DIR, filename)) as pdf:
                    for page in pdf.pages:
                        full_text += extract_page_text_with_tables(page) + "\n\n"
            elif filename.endswith('.txt'):
                with open(os.path.join(DOCS_DIR, filename), 'r', encoding='utf-8') as f:
                    full_text = f.read()
        except Exception as e:
            print(f"   ❌ Failed to read {filename}: {e}. Aborting.")
            return
        
        for chunk in chunk_text(full_text, max_chars=1000, overlap=200):
            enriched_chunk = f"[Source Document: {filename}]\n{chunk}"
            documents.append(enriched_chunk)
            metadatas.append({"source": filename, "page": 1})
            ids.append(f"doc_{chunk_id}")
            chunk_id += 1

    print(f"2. Successfully read {len(documents)} chunks into memory.")
    print("3. Connecting to ChromaDB...")
    
    client = chromadb.PersistentClient(path=DB_DIR)
    try: client.delete_collection(name=COLLECTION_NAME)
    except: pass
        
    embed_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    collection = client.create_collection(name=COLLECTION_NAME, embedding_function=embed_func, metadata={"hnsw:space": "cosine"})

    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    print(f"✅ Success! Database rebuilt with {len(documents)} chunks.")

if __name__ == "__main__":
    build_knowledge_base()