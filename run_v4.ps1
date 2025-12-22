# WhisperX Pipeline v4 - Запуск
# Использование: .\run_v4.ps1 или .\run_v4.ps1 "путь\к\файлу.mp4"

param(
    [string]$InputFile = "2025-12-02_совещание Кравт, Северин, Powerchina_Бытов.городок ПОС.mp4"
)

# Активируем venv
& "$PSScriptRoot\venv\Scripts\Activate.ps1"

# Запуск пайплайна
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "WhisperX Pipeline v4 (Optimized)" -ForegroundColor Cyan
Write-Host "Файл: $InputFile" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Cyan

python "$PSScriptRoot\test_multilang_v4.py" "$InputFile"

Write-Host ""
Write-Host "Готово! Результаты в папке output/" -ForegroundColor Green
