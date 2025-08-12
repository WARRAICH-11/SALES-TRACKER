# LLM Models Directory

This directory should contain the local LLM model file for AI Q&A functionality.

## Required Model

Place a GGUF 4-bit quantized model file here named `model.gguf`.

### Recommended Models:
- **Llama 3.1 8B Q4_K_M** (~4.9GB) - Best balance of quality and speed
- **Mistral 7B v0.3 Q4_K_M** (~4.1GB) - Faster, good quality
- **Phi-3 Mini 4K Q4_K_M** (~2.4GB) - Smallest, fastest

### Download Sources:
- [Hugging Face](https://huggingface.co/models?library=gguf)
- [TheBloke's GGUF models](https://huggingface.co/TheBloke)

### Example Download (Llama 3.1 8B):
```bash
# Using huggingface-hub
pip install huggingface-hub
huggingface-cli download microsoft/Phi-3-mini-4k-instruct-gguf Phi-3-mini-4k-instruct-q4.gguf --local-dir . --local-dir-use-symlinks False
mv Phi-3-mini-4k-instruct-q4.gguf model.gguf
```

### Alternative: Disable AI Features
If you don't want to use AI features, they will gracefully degrade when no model is found.

## File Structure
```
models/llm/
├── README.md (this file)
└── model.gguf (your downloaded model)
```
