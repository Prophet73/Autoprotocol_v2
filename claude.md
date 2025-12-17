# WhisperX Pipeline

## О проекте
Полный пайплайн для обработки аудио/видео записей совещаний:
- **Транскрипция** — WhisperX (large-v3), 70x realtime
- **Диаризация** — pyannote-audio, идентификация спикеров
- **Эмоции** — Aniemore (русская модель wav2vec2)
- **Отчёты** — Word + TXT с профилями спикеров

## Требования
- Python 3.10
- NVIDIA GPU с CUDA (8+ GB VRAM)
- FFmpeg
- HuggingFace токен (для pyannote)

## Установка

### Windows
```powershell
# Создать venv
python -m venv venv
.\venv\Scripts\Activate.ps1

# PyTorch с CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Зависимости
pip install -r requirements.txt
```

### Ubuntu
```bash
# Системные зависимости
sudo apt update
sudo apt install ffmpeg python3.10 python3.10-venv

# Создать venv
python3.10 -m venv venv
source venv/bin/activate

# PyTorch с CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Зависимости
pip install -r requirements.txt
```

## Настройка HuggingFace токена
1. Создать аккаунт: https://huggingface.co
2. Принять условия pyannote: https://huggingface.co/pyannote/speaker-diarization-3.1
3. Создать токен: https://huggingface.co/settings/tokens
4. Добавить в `.env`:
```
HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxx
```

## Использование

### CLI
```bash
# Базовое использование
python transcribe_full.py video.mp4

# С параметрами
python transcribe_full.py video.mp4 -m large-v3 -l ru -o ./results

# Без анализа эмоций (быстрее)
python transcribe_full.py video.mp4 --skip-emotions

# CPU режим
python transcribe_full.py video.mp4 -d cpu --compute-type int8

# Справка
python transcribe_full.py --help
```

### Python API
```python
from pathlib import Path
from transcribe_full import process_file

result = process_file(
    input_file=Path("video.mp4"),
    output_dir=Path("./output"),
    model="large-v3",
    language="ru",
    device="cuda"
)
print(f"Результат: {result}")
```

## Параметры CLI

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `input` | — | Входной файл (обязательный) |
| `-o, --output` | `./output` | Папка для результатов |
| `-m, --model` | `large-v3` | Модель Whisper |
| `-l, --language` | `ru` | Язык |
| `-d, --device` | `cuda` | Устройство (cuda/cpu) |
| `--compute-type` | `float16` | Тип вычислений |
| `--batch-size` | `16` | Размер батча |
| `--skip-emotions` | `false` | Пропустить эмоции |
| `--hf-token` | из .env | HuggingFace токен |
| `--open` | `false` | Открыть результат (Windows) |

## Выходные файлы
- `protocol_YYYYMMDD_HHMMSS.docx` — Word отчёт
- `protocol_YYYYMMDD_HHMMSS.txt` — текстовый отчёт

### Структура отчёта
1. **Информация о записи** — файл, дата, длительность
2. **Профиль участников** — время, эмоции, интерпретация
3. **Статистика эмоций** — общая по всем спикерам
4. **Транскрипция** — с таймкодами, спикерами, эмоциями

## Модели эмоций
Используется русская модель: `Aniemore/wav2vec2-xlsr-53-russian-emotion-recognition`

Классы:
- 😐 neutral — Нейтрально
- 😊 positive — Позитив
- 😔 sad — Грусть
- 😠 angry — Раздражение
- 🤔 other — Другое

## PyTorch 2.8+ Workaround
Скрипт содержит патч для совместимости с PyTorch 2.8+:
```python
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load
```

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| CUDA out of memory | Уменьшить `--batch-size` или модель |
| FFmpeg not found | Установить FFmpeg, добавить в PATH |
| weights_only error | Патч уже включён в скрипт |
| Диаризация не работает | Проверить HF_TOKEN и права доступа |

## Структура проекта
```
WhisperX/
├── transcribe_full.py   # Основной скрипт
├── requirements.txt     # Зависимости
├── .env                 # Токены (не в git)
├── .gitignore
├── claude.md            # Документация
├── output/              # Результаты (не в git)
└── venv/                # Окружение (не в git)
```

## Производительность
Тестировано на RTX 4060 Ti (16GB):
- 58 мин видео → ~4.5 мин обработки
- Модель large-v3, batch_size=16
