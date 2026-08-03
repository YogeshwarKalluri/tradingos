#!/usr/bin/env python3
"""
TradingOS Setup Script
Sets up the local development environment.
Run: python scripts/setup.py
"""

import subprocess
import sys
import os
import venv
from pathlib import Path

def run_cmd(cmd, cwd=None, check=True):
    """Run command and return result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr and check:
        print(f"STDERR: {result.stderr}")
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")
    return result

def check_python_version():
    """Verify Python 3.11+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        raise RuntimeError(f"Python 3.11+ required, found {version.major}.{version.minor}")
    print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")

def check_gpu():
    """Check for NVIDIA GPU and CUDA."""
    try:
        result = run_cmd("nvidia-smi", check=False)
        if result.returncode == 0:
            print("[OK] NVIDIA GPU detected")
            # Parse GPU info
            for line in result.stdout.split('\n'):
                if 'RTX' in line or 'GTX' in line:
                    print(f"  {line.strip()}")
        else:
            print("[WARN] No NVIDIA GPU detected (nvidia-smi failed)")
    except FileNotFoundError:
        print("[WARN] nvidia-smi not found")

def create_venv(project_root):
    """Create virtual environment."""
    venv_path = project_root / ".venv"
    if venv_path.exists():
        print(f"[OK] Virtual environment already exists at {venv_path}")
        return venv_path
    
    print("Creating virtual environment...")
    venv.create(venv_path, with_pip=True)
    print(f"[OK] Created virtual environment at {venv_path}")
    return venv_path

def get_python(venv_path):
    """Get python executable path."""
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"

def install_dependencies(venv_path, project_root):
    """Install Python dependencies."""
    python = get_python(venv_path)
    
    # Upgrade pip first
    print("Upgrading pip...")
    run_cmd(f'"{python}" -m pip install --upgrade pip')
    
    # Install PyTorch with CUDA first (required for other packages)
    print("Installing PyTorch with CUDA...")
    run_cmd(f'"{python}" -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121')
    
    # Install llama-cpp-python with CUDA support (commented due to Windows long path issue)
    # print("Installing llama-cpp-python with CUDA...")
    # if sys.platform == "win32":
    #     # On Windows, try pre-built wheel first
    #     run_cmd(f'"{python}" -m pip install llama-cpp-python', check=False)
    # else:
    #     run_cmd('CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python')
    print("Skipping llama-cpp-python (Windows long path issue - install manually)")
    
    # Install remaining requirements
    req_file = project_root / "requirements.txt"
    if req_file.exists():
        print("Installing requirements.txt...")
        run_cmd(f'"{python}" -m pip install -r "{req_file}"')
    else:
        print("[WARN] requirements.txt not found")

def create_directories(project_root):
    """Create necessary data directories."""
    dirs = [
        "data",
        "logs",
        "models/vision",
        "models/reasoning", 
        "models/embedding",
        "models/speech",
        "cache",
    ]
    for d in dirs:
        (project_root / d).mkdir(parents=True, exist_ok=True)
    print("[OK] Created data directories")

def create_env_file(project_root):
    """Create .env template if not exists."""
    env_file = project_root / ".env"
    if env_file.exists():
        print("[OK] .env already exists")
        return
    
    template = """# TradingOS Environment Variables
# Copy to .env and fill in your values

# Market Data APIs
POLYGON_API_KEY=your_polygon_key
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret

# Optional: Other data providers
IEX_CLOUD_TOKEN=
FINNHUB_TOKEN=

# Broker (for live trading)
# ALPACA_API_KEY=
# ALPACA_SECRET_KEY=

# Model paths (relative to project root)
# MODEL_VISION_PATH=models/vision/yolo_v8_custom.engine
# MODEL_REASONING_PATH=models/reasoning/nemotron-3-ultra.Q4_K_M.gguf
# MODEL_EMBEDDING_PATH=models/embedding/bge-large-en-v1.5
# MODEL_SPEECH_PATH=models/speech/whisper-large-v3

# GPU Settings
CUDA_VISIBLE_DEVICES=0
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
"""
    env_file.write_text(template)
    print("[OK] Created .env template")

def verify_installation(venv_path):
    """Verify key imports work."""
    python = get_python(venv_path)
    
    test_imports = [
        "torch",
        "numpy",
        "pandas",
        "duckdb",
        "qdrant_client",
        "pydantic",
        "yaml",
    ]
    
    print("Verifying imports...")
    for mod in test_imports:
        cmd = f'"{python}" -c "import {mod}; print(\'  [OK] {mod} \' + __import__({mod}).__version__)"'
        result = run_cmd(cmd, check=False)
        if result.returncode != 0:
            print(f"  [FAIL] {mod}")
        else:
            print(result.stdout.strip())

def main():
    project_root = Path(__file__).parent.parent
    print(f"Setting up TradingOS in: {project_root}")
    print("=" * 50)
    
    check_python_version()
    check_gpu()
    create_directories(project_root)
    create_env_file(project_root)
    
    venv_path = create_venv(project_root)
    install_dependencies(venv_path, project_root)
    verify_installation(venv_path)
    
    print("=" * 50)
    print("[OK] Setup complete!")
    print()
    print("Next steps:")
    if sys.platform == "win32":
        print(f"  1. Activate venv: {venv_path}\\Scripts\\activate")
    else:
        print(f"  1. Activate venv: source {venv_path}/bin/activate")
    print("  2. Edit .env with your API keys")
    print("  3. Run: python scripts/download_models.py")
    print("  4. Start developing!")

if __name__ == "__main__":
    main()