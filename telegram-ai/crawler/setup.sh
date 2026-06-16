#!/bin/bash
# ============================================================================
# Telegram AI Crawler - Automated Setup Script (Linux/Mac)
# ============================================================================
# This script will:
# 1. Check for Python installation
# 2. Create virtual environment if not exists
# 3. Activate virtual environment
# 4. Upgrade pip
# 5. Install all dependencies (crawler, API, LLM, CLIP, ChromaDB)
# 6. Create necessary directories
# 7. Initialize configuration files
# 8. Test installations
# ============================================================================

set -e  # Exit on error

echo ""
echo "============================================================================"
echo " Telegram AI Crawler - Setup Script"
echo "============================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to script directory
cd "$(dirname "$0")"

# ============================================================================
# Step 1: Check Python Installation
# ============================================================================
echo "[1/8] Checking Python installation..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Python 3 is not installed"
    echo ""
    echo "Please install Python 3.8 or higher:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  MacOS: brew install python3"
    echo ""
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}[OK]${NC} Python $PYTHON_VERSION found"
echo ""

# ============================================================================
# Step 2: Create Virtual Environment
# ============================================================================
echo "[2/8] Setting up virtual environment..."

if [ -d "venv" ]; then
    echo -e "${GREEN}[OK]${NC} Virtual environment already exists"
else
    echo "Creating new virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}[OK]${NC} Virtual environment created"
fi
echo ""

# ============================================================================
# Step 3: Activate Virtual Environment
# ============================================================================
echo "[3/8] Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}[OK]${NC} Virtual environment activated"
echo ""

# ============================================================================
# Step 4: Upgrade pip
# ============================================================================
echo "[4/8] Upgrading pip..."
python -m pip install --upgrade pip --quiet
echo -e "${GREEN}[OK]${NC} pip upgraded"
echo ""

# ============================================================================
# Step 5: Install Dependencies
# ============================================================================
echo "[5/8] Installing dependencies..."
echo "This may take 5-10 minutes depending on your internet connection..."
echo ""

echo "Installing core dependencies..."
pip install telethon pyyaml requests flask flask-cors --quiet
echo -e "${GREEN}✓${NC} Core dependencies installed"

echo "Installing LLM providers..."
pip install anthropic openai --quiet
echo -e "${GREEN}✓${NC} LLM providers installed"

echo "Installing vector database..."
pip install chromadb --quiet
echo -e "${GREEN}✓${NC} ChromaDB installed"

echo "Installing text embeddings..."
pip install sentence-transformers --quiet
echo -e "${GREEN}✓${NC} Sentence transformers installed"

echo "Installing image processing..."
pip install Pillow tqdm --quiet
echo -e "${GREEN}✓${NC} Image processing libraries installed"

echo ""
echo "============================================================================"
echo "Installing PyTorch and CLIP..."
echo "This is the largest download (may take several minutes)"
echo "============================================================================"
echo ""

# Detect platform for PyTorch installation
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}[INFO]${NC} NVIDIA GPU detected, installing CUDA version of PyTorch..."
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
else
    echo -e "${YELLOW}[INFO]${NC} No NVIDIA GPU detected, installing CPU version of PyTorch..."
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi
echo -e "${GREEN}✓${NC} PyTorch installed"

echo "Installing CLIP from GitHub..."
pip install git+https://github.com/openai/CLIP.git --quiet || {
    echo -e "${YELLOW}[WARNING]${NC} Failed to install CLIP from GitHub"
    echo "Installing dependencies manually..."
    pip install ftfy regex --quiet
}
echo -e "${GREEN}✓${NC} CLIP installed"

echo -e "${GREEN}[OK]${NC} All dependencies installed"
echo ""

# ============================================================================
# Step 6: Create Necessary Directories
# ============================================================================
echo "[6/8] Creating necessary directories..."

mkdir -p api/uploads
mkdir -p crawler/vector_db
mkdir -p crawler/llm_cache
mkdir -p crawler/failed_extractions
mkdir -p logs

echo -e "${GREEN}[OK]${NC} Directories created"
echo ""

# ============================================================================
# Step 7: Initialize Configuration Files
# ============================================================================
echo "[7/8] Checking configuration files..."

if [ ! -f "crawler/config.py" ]; then
    echo -e "${YELLOW}[WARNING]${NC} crawler/config.py not found"
    echo "You need to create this file with your Telegram API credentials"
    echo ""
    echo "Example content:"
    echo "api_id = 12345678"
    echo "api_hash = 'your_api_hash_here'"
    echo "phone_number = '+998901234567'"
    echo "session_name = 'main_session'"
    echo ""
fi

if [ ! -f "crawler/schemas/product_listing.yaml" ]; then
    echo -e "${YELLOW}[WARNING]${NC} Schema files not found in crawler/schemas/"
    echo "Make sure schema YAML files are present"
fi

echo -e "${GREEN}[OK]${NC} Configuration check complete"
echo ""

# ============================================================================
# Step 8: Test Installation
# ============================================================================
echo "[8/8] Testing installation..."
echo ""

echo "Testing Python imports..."
python -c "import telethon; print('✓ Telethon')" 2>/dev/null || echo "✗ Telethon"
python -c "import anthropic; print('✓ Anthropic')" 2>/dev/null || echo "✗ Anthropic"
python -c "import chromadb; print('✓ ChromaDB')" 2>/dev/null || echo "✗ ChromaDB"
python -c "import torch; print('✓ PyTorch')" 2>/dev/null || echo "✗ PyTorch"
python -c "import sentence_transformers; print('✓ Sentence Transformers')" 2>/dev/null || echo "✗ Sentence Transformers"
python -c "import PIL; print('✓ Pillow')" 2>/dev/null || echo "✗ Pillow"
python -c "import flask; print('✓ Flask')" 2>/dev/null || echo "✗ Flask"

echo ""
echo "Testing CLIP installation..."
python -c "import clip; print('✓ CLIP loaded successfully')" 2>/dev/null || {
    echo -e "${YELLOW}[WARNING]${NC} CLIP not installed properly"
    echo "You may need to install manually:"
    echo "pip install git+https://github.com/openai/CLIP.git"
}

echo ""
echo "Testing CUDA availability..."
python -c "import torch; print('✓ CUDA available' if torch.cuda.is_available() else '⚠ CUDA not available (using CPU)')"

echo ""

# ============================================================================
# Create helper scripts
# ============================================================================
echo "Creating helper scripts..."

# Create start_api.sh
cat > start_api.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
cd api
echo "Starting API Server..."
python server_llm.py
EOF
chmod +x start_api.sh

# Create start_crawler.sh
cat > start_crawler.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
cd crawler
echo "Starting Crawler..."
python FlexibleCrawler.py
EOF
chmod +x start_crawler.sh

# Create test_llm.sh
cat > test_llm.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
cd crawler
echo "Testing LLM Configuration..."
python llm_config.py
EOF
chmod +x test_llm.sh

# Create test_clip.sh
cat > test_clip.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
cd crawler
echo "Testing CLIP Image Embeddings..."
python image_embeddings.py
EOF
chmod +x test_clip.sh

echo -e "${GREEN}[OK]${NC} Helper scripts created"
echo ""

# ============================================================================
# Display Summary
# ============================================================================
echo "============================================================================"
echo " Setup Complete!"
echo "============================================================================"
echo ""
echo "Virtual Environment: venv/"
echo "Python Version: $PYTHON_VERSION"
echo ""
echo "Next Steps:"
echo ""
echo "1. Configure API Keys:"
echo "   - Edit crawler/llm_config.py"
echo "   - Set ANTHROPIC_API_KEY or OPENAI_API_KEY"
echo "   - Get key from: https://console.anthropic.com/"
echo ""
echo "2. Configure Telegram Credentials:"
echo "   - Edit crawler/config.py"
echo "   - Set api_id, api_hash, phone_number"
echo "   - Get from: https://my.telegram.org"
echo ""
echo "3. Configure Channels:"
echo "   - Edit schema files in crawler/schemas/"
echo "   - Add your channel usernames"
echo ""
echo "4. Test Components:"
echo "   - Run: ./test_llm.sh (test LLM configuration)"
echo "   - Run: ./test_clip.sh (test CLIP embeddings)"
echo ""
echo "5. Start the System:"
echo "   - Run: ./start_api.sh (start API server)"
echo "   - Run: ./start_crawler.sh (start crawler)"
echo ""
echo "Helper Commands:"
echo "   ./test_llm.sh       - Test LLM configuration"
echo "   ./test_clip.sh      - Test CLIP embeddings"
echo "   ./start_api.sh      - Start API server"
echo "   ./start_crawler.sh  - Start crawler"
echo ""
echo "Documentation:"
echo "   LLM_CRAWLER_GUIDE.md - Complete usage guide"
echo "   LLM_IMPLEMENTATION_SUMMARY.md - Implementation details"
echo "   FLEXIBLE_SCHEMA_GUIDE.md - Schema creation guide"
echo ""
echo "============================================================================"
echo " Cost Estimate:"
echo "   - LLM (text extraction): ~\$3 per 1000 messages"
echo "   - Image embeddings: FREE (CLIP runs locally)"
echo "   - Vector search: FREE (ChromaDB)"
echo "   - Total: ~\$3-5 per 1000 messages"
echo "============================================================================"
echo ""

# Check if API keys are configured
echo "Checking configuration status..."
echo ""

if grep -q "your-anthropic-api-key-here" crawler/llm_config.py 2>/dev/null; then
    echo -e "${YELLOW}[!] WARNING:${NC} Anthropic API key not configured"
    echo "    Edit crawler/llm_config.py and set ANTHROPIC_API_KEY"
    echo ""
fi

if [ -f "crawler/config.py" ]; then
    if grep -q "your_api_hash" crawler/config.py 2>/dev/null; then
        echo -e "${YELLOW}[!] WARNING:${NC} Telegram credentials not configured"
        echo "    Edit crawler/config.py and set api_id, api_hash, phone_number"
        echo ""
    fi
else
    echo -e "${YELLOW}[!] WARNING:${NC} crawler/config.py not found"
    echo "    Create this file with your Telegram API credentials"
    echo ""
fi

echo "============================================================================"
echo ""
echo "Ready to start!"
echo ""
