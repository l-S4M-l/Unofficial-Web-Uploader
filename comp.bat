@echo off
call .venv\Scripts\activate
pyinstaller -w --onefile --icon icon.ico main.py