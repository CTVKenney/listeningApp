# Chinese Listening Practice App

A desktop app for practicing Chinese listening: you hear a sentence first, then reveal the Chinese text, pinyin, and English translation in stages.

## User Guide

### What you need

- Python 3.12+
- AWS credentials configured on your machine
- Read access to S3 bucket `chineselisteningpractice` (for `metadata.json` and `sample_*.mp3`)
- Python packages: `PyQt6`, `boto3`

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install PyQt6 boto3
```

### Run the app

```bash
python3 app.py
```

### How to use the app

1. Click `Start` to fetch a random sentence and play audio.
2. Click `Replay` to hear the same sentence again.
3. Click `Show` to reveal Chinese characters and pinyin.
4. Click `Show English` to reveal the translation.
5. Click `Start` again for a new sentence.
6. Click `Exit` when finished.

### Notes

- Audio and metadata are fetched from AWS S3 each session (internet required).
- Downloaded temporary files are cleaned up on exit (`downloaded_*`).
- If AWS credentials or bucket permissions are missing, the app cannot load content.
- `app.py` currently forces Qt multimedia plugin `coreaudio` (macOS). If audio does not play on Linux/Windows, update/remove that environment setting.

## Developer Guide

### Tech stack

- Python desktop UI: PyQt6
- AWS SDK: boto3 (S3 + Polly)
- Tests: `unittest`
- Build/test runner: Bazel

### Dev setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install PyQt6 boto3 pypinyin
```

`pypinyin` is needed for `add_pinyin.py`.

### Run tests

```bash
bazel test //:unit_tests
```

This runs:

- `//:test_app`
- `//:test_generate_audio`
- `//:test_add_pinyin`

### Main files

- `app.py`: GUI app that downloads metadata/audio from S3 and drives the listen/reveal flow.
- `generate_audio.py`: Reads TSV sentence pairs, deduplicates Chinese text, synthesizes MP3 with Polly, uploads audio, and updates metadata.
- `add_pinyin.py`: Reads metadata from S3, computes pinyin from `characters`, writes updated metadata back to S3.
- `tests/`: Unit tests for app flow and data scripts.

### Data pipeline scripts

Generate audio + metadata entries:

```bash
python3 generate_audio.py
```

Populate/refresh pinyin in metadata:

```bash
python3 add_pinyin.py
```

Both scripts use default bucket/key values in code:

- Bucket: `chineselisteningpractice`
- Metadata key: `metadata.json`
- TSV key: `ChineseEnglishSentencePairs.tsv` (for audio generation)

### AWS credentials

All AWS access uses boto3's default credential chain. For local dev, configure credentials with one of:

- `aws configure`
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`)
- Shared credentials/config files

Minimum practical permissions:

- S3 read for app playback
- S3 read/write for metadata/audio scripts
- Polly `synthesize_speech` for audio generation
