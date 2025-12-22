#!/usr/bin/env python3
"""Check available VAD options"""

# Option 1: silero-vad package
try:
    from silero_vad import load_silero_vad
    print("silero_vad package: OK")
except ImportError as e:
    print(f"silero_vad package: NOT FOUND ({e})")

# Option 2: torch.hub silero
try:
    import torch
    model, utils = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        trust_repo=True
    )
    print("silero via torch.hub: OK")
    print(f"  utils: {list(utils.keys()) if isinstance(utils, dict) else utils}")
except Exception as e:
    print(f"silero via torch.hub: FAILED ({e})")

# Option 3: pyannote VAD
try:
    from pyannote.audio import Pipeline
    print("pyannote.audio: OK (can use for VAD)")
except ImportError as e:
    print(f"pyannote.audio: NOT FOUND ({e})")

# Option 4: whisperx internal vad
try:
    from whisperx.vad import load_vad_model
    print("whisperx.vad: OK")
except ImportError as e:
    print(f"whisperx.vad: NOT FOUND ({e})")

print("\nDone!")
