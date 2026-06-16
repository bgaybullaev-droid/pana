@echo off
call venv\Scripts\activate.bat
cd crawler
echo Testing LLM Configuration...
python llm_config.py
pause
