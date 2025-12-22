@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: WhisperX Pipeline v4 - Запуск
:: Использование: run_v4.bat или run_v4.bat "путь\к\файлу.mp4"

set "SCRIPT_DIR=%~dp0"
set "INPUT_FILE=%~1"

if "%INPUT_FILE%"=="" (
    set "INPUT_FILE=2025-12-02_совещание Кравт, Северин, Powerchina_Бытов.городок ПОС.mp4"
)

echo ============================================================
echo WhisperX Pipeline v4 (Optimized + Debug)
echo Файл: %INPUT_FILE%
echo ============================================================

:: Активируем venv и запускаем
call "%SCRIPT_DIR%venv\Scripts\activate.bat"
python "%SCRIPT_DIR%test_multilang_v4.py" "%INPUT_FILE%"

echo.
echo Результаты в папке output/
echo - v4_*.docx - Word отчёт
echo - v4_*.json - данные
echo - v4_debug_*.json - полный debug лог для анализа
pause
