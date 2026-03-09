@echo off
echo.
echo  ==========================================
echo   SkillOS - Starting Backend Server
echo  ==========================================
echo.

set SKILLOS_SECRET_KEY=skillos-secret-key-change-in-production
set PHASE_AUTH=true
set PHASE_SKILLS=true
set SKILLOS_ENV=development

echo  Seeding 12 problems...
python -m skillos.db.seed_problems

echo.
echo  Starting server on http://localhost:8000
echo  Press Ctrl+C to stop
echo.

python -m skillos.main
pause
