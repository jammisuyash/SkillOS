@echo off
setlocal EnableDelayedExpansion

REM SkillOS -- Start Backend (FastAPI / uvicorn -- DEFAULT)
REM Usage: Double-click or run from cmd

REM Load .env if it exists
if exist .env (
    echo   Loading .env...
    for /f "usebackq tokens=1,2 delims==" %%A in (".env") do (
        set line=%%A
        if not "!line:~0,1!"=="#" if not "%%A"=="" set %%A=%%B
    )
)

if "%SKILLOS_SECRET_KEY%"=="" set SKILLOS_SECRET_KEY=skillos-secret-key-change-in-production
if "%SKILLOS_ENV%"=="" set SKILLOS_ENV=development
if "%PHASE_AUTH%"=="" set PHASE_AUTH=true
if "%PHASE_SKILLS%"=="" set PHASE_SKILLS=true
if "%SKILLOS_USE_DOCKER%"=="" set SKILLOS_USE_DOCKER=auto

echo.
echo  ============================================================
echo   SkillOS -- FastAPI Backend (replaces old http.server)
echo  ============================================================
echo.
echo   Server:     http://localhost:8000
echo   Swagger UI: http://localhost:8000/docs
echo   ReDoc:      http://localhost:8000/redoc
echo.

REM Check FastAPI is installed
python -c "import fastapi, uvicorn" 2>nul
if %errorlevel% neq 0 (
    echo   Installing FastAPI + uvicorn...
    pip install "fastapi[all]" "uvicorn[standard]" --quiet
)

REM AI Provider Status
echo   AI Providers ^(fallback: Groq ^> Gemini ^> Anthropic ^> OpenAI^):
if defined GROQ_API_KEY      (echo     [OK] Groq       configured) else (echo     [ ] Groq       ^(add GROQ_API_KEY to .env^))
if defined GEMINI_API_KEY    (echo     [OK] Gemini     configured) else (echo     [ ] Gemini     ^(add GEMINI_API_KEY to .env^))
if defined ANTHROPIC_API_KEY (echo     [OK] Anthropic  configured) else (echo     [ ] Anthropic  ^(add ANTHROPIC_API_KEY to .env^))
if defined OPENAI_API_KEY    (echo     [OK] OpenAI     configured) else (echo     [ ] OpenAI     ^(add OPENAI_API_KEY to .env^))
echo.

echo   Press Ctrl+C to stop
echo.

REM Start FastAPI Server
uvicorn skillos.api.fastapi_app:app --host 0.0.0.0 --port 8000 --reload --reload-dir skillos --log-level info
pause
