# Embeddings Models Directory

This directory is used for storing sentence transformer models for RAG (Retrieval Augmented Generation) functionality.

## Auto-Download

The application will automatically download the required `all-MiniLM-L6-v2` model on first use. No manual setup required.

## Model Details

- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Size**: ~90MB
- **Purpose**: Converting text to embeddings for semantic search
- **Auto-downloaded to**: `~/.cache/torch/sentence_transformers/`

## Manual Download (Optional)

If you want to pre-download the model:

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
```

## File Structure After First Run
```
models/embeddings/
├── README.md (this file)
└── (models auto-downloaded to system cache)
```
