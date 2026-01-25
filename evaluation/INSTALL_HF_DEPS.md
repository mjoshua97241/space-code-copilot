# Hugging Face VLM Dependencies Installation

This guide explains how to install the required dependencies for evaluating the Hugging Face FloorPlanVisionAIAdaptor model.

## Required Dependencies

1. **PyTorch** (torch) - Deep learning framework
2. **unsloth** - Efficient fine-tuning and inference library
3. **transformers** - Hugging Face transformers library
4. **bitsandbytes** - For 4-bit quantization (optional, but recommended for memory efficiency)
5. **pillow** - Image processing (already in project dependencies)
6. **PyMuPDF** (fitz) - PDF processing (already in project dependencies as `pymupdf`)

## Installation Options

### Option 1: CPU-Only Installation (Slower, but works on any machine)

```bash
cd /home/mj/workspace/space-code-copilot/backend

# Install PyTorch CPU version
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies
uv pip install unsloth transformers bitsandbytes
```

**Note:** CPU inference will be **very slow** (10-100x slower than GPU). Only use this if you don't have GPU access.

### Option 2: GPU Installation (Recommended - Much Faster)

#### For CUDA 11.8:
```bash
cd /home/mj/workspace/space-code-copilot/backend

# Install PyTorch with CUDA 11.8 support
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
uv pip install unsloth transformers bitsandbytes
```

#### For CUDA 12.1:
```bash
cd /home/mj/workspace/space-code-copilot/backend

# Install PyTorch with CUDA 12.1 support
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install other dependencies
uv pip install unsloth transformers bitsandbytes
```

#### For CUDA 12.4:
```bash
cd /home/mj/workspace/space-code-copilot/backend

# Install PyTorch with CUDA 12.4 support
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Install other dependencies
uv pip install unsloth transformers bitsandbytes
```

## Check Your CUDA Version

To determine which CUDA version you have:

```bash
nvcc --version
# or
nvidia-smi
```

## Verify Installation

After installation, verify that PyTorch can detect your GPU (if available):

```bash
cd /home/mj/workspace/space-code-copilot/backend
uv run python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')"
```

## Running Evaluation

Once dependencies are installed, you can run the evaluation:

```bash
cd /home/mj/workspace/space-code-copilot/backend
uv run python ../evaluation/vlm_evaluation.py
```

The script will:
- Auto-detect CPU or GPU
- Warn you if running on CPU (will be slow)
- Evaluate GPT-4o, Gemini 2.0 Flash, and Hugging Face FloorPlanVisionAIAdaptor
