````markdown
# LEXGUARD - Phase 1: Institutional Memory (Knowledge Graph Pipeline)

This module handles the ingestion of unstructured legal documents (like Lease Agreements and NDAs) and converts them into a structured, queryable KùzuDB Knowledge Graph. It uses a Neuro-Symbolic architecture optimized for low-RAM local environments.

## Architecture Overview

1. **Sliding Window Chunking:** Prevents context loss by overlapping document chunks.
2. **The Scout Pass (LLM):** Dynamically reads the preamble to map generic roles (e.g., "Lessee") to specific legal entities (e.g., "Force10 Networks").
3. **The Deep Read (spaCy NER):** Deterministically extracts Companies and People, filtering out mathematical noise and formatting artifacts.
4. **Relationship Parsing (LLM):** Uses `qwen2.5:3b` to logically connect the extracted entities.
5. **Fuzzy Matching Sanitizer:** Intercepts LLM hallucinations and typos to ensure clean database insertion.

## Prerequisites

1. **Python 3.8+**
2. **Ollama** installed locally.
3. Pull the required lightweight model:
   ```bash
   ollama pull qwen2.5:3b
   ```
````

## Installation

1. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Download the local spaCy English model:
   ```bash
   python -m spacy download en_core_web_sm
   ```

## How to Run the Pipeline

**1. Initialize the Database:**
Ensure `reset=True` is set in the `graph_manager.py` test block to wipe old data, then run:

```bash
python graph_manager.py
```

_(Remember to set `reset=False` after initializing!)_

**2. Ingest a Legal Document:**
Place your PDF in the root directory, update the file path at the bottom of `ingester.py`, and run:

```bash
python ingester.py
```

**3. View the Graph Data:**
To print the structured relationships extracted from the document:

```bash
python view_graph.py
```
