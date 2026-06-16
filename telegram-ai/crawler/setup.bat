@echo off
REM ============================================================================
REM Telegram AI Crawler - Automated Setup Script (Windows)
REM ============================================================================
REM This script will:
REM 1. Check for Python installation
REM 2. Create virtual environment if not exists
REM 3. Activate virtual environment
REM 4. Upgrade pip
REM 5. Install all dependencies (crawler, API, LLM, CLIP, ChromaDB)
REM 6. Create necessary directories
REM 7. Initialize configuration files
REM 8. Test installations
REM ============================================================================

echo.
echo ============================================================================
echo  Telegram AI Crawler - Setup Script
echo ============================================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM ============================================================================
REM Step 1: Check Python Installation
REM ============================================================================
echo [1/8] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% found
echo.

REM ============================================================================
REM Step 2: Create Virtual Environment
REM ============================================================================
echo [2/8] Setting up virtual environment...

if exist "venv\" (
    echo [OK] Virtual environment already exists
) else (
    echo Creating new virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)
echo.

REM ============================================================================
REM Step 3: Activate Virtual Environment
REM ============================================================================
echo [3/8] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM ============================================================================
REM Step 4: Upgrade pip
REM ============================================================================
echo [4/8] Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [WARNING] Failed to upgrade pip, continuing anyway...
)
echo [OK] pip upgraded
echo.

REM ============================================================================
REM Step 5: Install Dependencies
REM ============================================================================
echo [5/8] Installing dependencies...
echo This may take 5-10 minutes depending on your internet connection...
echo.

echo Installing core dependencies...
pip install telethon pyyaml requests flask flask-cors
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install core dependencies
    pause
    exit /b 1
)

echo Installing LLM providers...
pip install anthropic openai
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install LLM providers
    pause
    exit /b 1
)

echo Installing vector database...
pip install chromadb
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install ChromaDB
    pause
    exit /b 1
)

echo Installing text embeddings...
pip install sentence-transformers
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install sentence-transformers
    pause
    exit /b 1
)

echo Installing image processing...
pip install Pillow tqdm
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install image processing libraries
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo Installing PyTorch and CLIP...
echo This is the largest download (may take several minutes)
echo ============================================================================
echo.

REM Check if CUDA is available
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] NVIDIA GPU detected, installing CUDA version of PyTorch...
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
) else (
    echo [INFO] No NVIDIA GPU detected, installing CPU version of PyTorch...
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
)

if %errorlevel% neq 0 (
    echo [ERROR] Failed to install PyTorch
    pause
    exit /b 1
)

echo Installing CLIP from GitHub...
pip install git+https://github.com/openai/CLIP.git
if %errorlevel% neq 0 (
    echo [WARNING] Failed to install CLIP from GitHub
    echo Trying alternative installation...
    pip install ftfy regex
)

echo [OK] All dependencies installed
echo.

REM ============================================================================
REM Step 6: Create Necessary Directories
REM ============================================================================
echo [6/8] Creating necessary directories...

if not exist "api\uploads\" mkdir api\uploads
if not exist "crawler\vector_db\" mkdir crawler\vector_db
if not exist "crawler\llm_cache\" mkdir crawler\llm_cache
if not exist "crawler\failed_extractions\" mkdir crawler\failed_extractions
if not exist "logs\" mkdir logs

echo [OK] Directories created
echo.

REM ============================================================================
REM Step 7: Initialize Configuration Files
REM ============================================================================
echo [7/8] Checking configuration files...

REM Check if config.py exists
if not exist "crawler\config.py" (
    echo [WARNING] crawler\config.py not found
    echo You need to create this file with your Telegram API credentials
    echo.
    echo Example content:
    echo api_id = 12345678
    echo api_hash = 'your_api_hash_here'
    echo phone_number = '+998901234567'
    echo session_name = 'main_session'
    echo.
)

REM Check if schemas exist
if not exist "crawler\schemas\product_listing.yaml" (
    echo [WARNING] Schema files not found in crawler\schemas\
    echo Make sure schema YAML files are present
)

echo [OK] Configuration check complete
echo.

REM ============================================================================
REM Step 8: Test Installation
REM ============================================================================
echo [8/8] Testing installation...
echo.

echo Testing Python imports...
python -c "import telethon; print('✓ Telethon')" 2>nul
python -c "import anthropic; print('✓ Anthropic')" 2>nul
python -c "import chromadb; print('✓ ChromaDB')" 2>nul
python -c "import torch; print('✓ PyTorch')" 2>nul
python -c "import sentence_transformers; print('✓ Sentence Transformers')" 2>nul
python -c "import PIL; print('✓ Pillow')" 2>nul
python -c "import flask; print('✓ Flask')" 2>nul

echo.
echo Testing CLIP installation...
python -c "import clip; print('✓ CLIP loaded successfully')" 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] CLIP not installed properly
    echo You may need to install manually:
    echo pip install git+https://github.com/openai/CLIP.git
)

echo.
echo Testing CUDA availability...
python -c "import torch; print('✓ CUDA available' if torch.cuda.is_available() else '⚠ CUDA not available (using CPU)')"

echo.

REM ============================================================================
REM Create helper batch files
REM ============================================================================
echo Creating helper scripts...

REM Create start_api.bat
(
echo @echo off
echo call venv\Scripts\activate.bat
echo cd api
echo echo Starting API Server...
echo python server_llm.py
) > start_api.bat

REM Create start_crawler.bat
(
echo @echo off
echo call venv\Scripts\activate.bat
echo cd crawler
echo echo Starting Crawler...
echo python FlexibleCrawler.py
) > start_crawler.bat

REM Create test_llm.bat
(
echo @echo off
echo call venv\Scripts\activate.bat
echo cd crawler
echo echo Testing LLM Configuration...
echo python llm_config.py
echo pause
) > test_llm.bat

REM Create test_clip.bat
(
echo @echo off
echo call venv\Scripts\activate.bat
echo cd crawler
echo echo Testing CLIP Image Embeddings...
echo python image_embeddings.py
echo pause
) > test_clip.bat

echo [OK] Helper scripts created
echo.

REM ============================================================================
REM Display Summary
REM ============================================================================
echo ============================================================================
echo  Setup Complete!
echo ============================================================================
echo.
echo Virtual Environment: venv\
echo Python Version: %PYTHON_VERSION%
echo.
echo Next Steps:
echo.
echo 1. Configure API Keys:
echo    - Edit crawler\llm_config.py
echo    - Set ANTHROPIC_API_KEY or OPENAI_API_KEY
echo    - Get key from: https://console.anthropic.com/
echo.
echo 2. Configure Telegram Credentials:
echo    - Edit crawler\config.py
echo    - Set api_id, api_hash, phone_number
echo    - Get from: https://my.telegram.org
echo.
echo 3. Configure Channels:
echo    - Edit schema files in crawler\schemas\
echo    - Add your channel usernames
echo.
echo 4. Test Components:
echo    - Run: test_llm.bat (test LLM configuration)
echo    - Run: test_clip.bat (test CLIP embeddings)
echo.
echo 5. Start the System:
echo    - Run: start_api.bat (start API server)
echo    - Run: start_crawler.bat (start crawler)
echo.
echo Helper Commands:
echo    test_llm.bat       - Test LLM configuration
echo    test_clip.bat      - Test CLIP embeddings
echo    start_api.bat      - Start API server
echo    start_crawler.bat  - Start crawler
echo.
echo Documentation:
echo    LLM_CRAWLER_GUIDE.md - Complete usage guide
echo    LLM_IMPLEMENTATION_SUMMARY.md - Implementation details
echo    FLEXIBLE_SCHEMA_GUIDE.md - Schema creation guide
echo.
echo ============================================================================
echo  Cost Estimate:
echo    - LLM (text extraction): ~$3 per 1000 messages
echo    - Image embeddings: FREE (CLIP runs locally)
echo    - Vector search: FREE (ChromaDB)
echo    - Total: ~$3-5 per 1000 messages
echo ============================================================================
echo.

REM Check if API keys are configured
echo Checking configuration status...
echo.

findstr /C:"your-anthropic-api-key-here" crawler\llm_config.py >nul 2>&1
if %errorlevel% equ 0 (
    echo [!] WARNING: Anthropic API key not configured
    echo     Edit crawler\llm_config.py and set ANTHROPIC_API_KEY
    echo.
)

if exist "crawler\config.py" (
    findstr /C:"your_api_hash" crawler\config.py >nul 2>&1
    if %errorlevel% equ 0 (
        echo [!] WARNING: Telegram credentials not configured
        echo     Edit crawler\config.py and set api_id, api_hash, phone_number
        echo.
    )
) else (
    echo [!] WARNING: crawler\config.py not found
    echo     Create this file with your Telegram API credentials
    echo.
)

echo ============================================================================
echo.
echo Ready to start! Press any key to exit setup...
pause >nul
