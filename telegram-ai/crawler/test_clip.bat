@echo off
call venv\Scripts\activate.bat
cd crawler
echo Testing CLIP Image Embeddings...
python image_embeddings.py
pause
