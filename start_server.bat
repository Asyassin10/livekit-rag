@echo off
REM Start the FastAPI token server
REM This provides the /token endpoint for the web client

echo.
echo 🚀 Starting FastAPI Token Server...
echo 📍 Server will run on http://localhost:8000
echo 📚 API Docs: http://localhost:8000/docs
echo.
echo To stop: Press Ctrl+C
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Run the server
python server.py

pause
