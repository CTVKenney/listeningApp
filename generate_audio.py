#!/usr/bin/env python3

import csv
import io
import json

DEFAULT_BUCKET = "chineselisteningpractice"
DEFAULT_TSV_FILE_KEY = "ChineseEnglishSentencePairs.tsv"
DEFAULT_METADATA_FILE_KEY = "metadata.json"
DEFAULT_VOICE = "Zhiyu"
DEFAULT_LANGUAGE_CODE = "cmn-CN"
DEFAULT_TTS_SERVICE = "polly"


def create_boto3_client(service_name):
    import boto3
    return boto3.client(service_name)


def load_tsv_rows(s3_client, bucket_name, key):
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    tsv_content = response["Body"].read().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(tsv_content), delimiter="\t")
    return [row for row in reader if len(row) > 1]


def dedupe_sentences(rows):
    seen = set()
    deduped = []
    for row in rows:
        sentence = row[1].strip()
        if not sentence or sentence in seen:
            continue
        seen.add(sentence)
        deduped.append(sentence)
    return deduped


def load_metadata(s3_client, bucket_name, key):
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    return json.loads(response["Body"].read().decode("utf-8"))


def write_metadata(s3_client, bucket_name, key, metadata):
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(metadata, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )


def next_sample_id(metadata, minimum_start=2):
    samples = metadata.get("samples", [])
    max_existing = 0
    for sample in samples:
        sample_id = sample.get("id")
        if isinstance(sample_id, int) and sample_id > max_existing:
            max_existing = sample_id
    return max(minimum_start, max_existing + 1)


def synthesize_audio(polly_client, text, voice=DEFAULT_VOICE, language_code=DEFAULT_LANGUAGE_CODE):
    response = polly_client.synthesize_speech(
        OutputFormat="mp3",
        Text=text,
        VoiceId=voice,
        TextType="text",
        LanguageCode=language_code,
    )
    return response["AudioStream"].read()


def upload_audio(s3_client, bucket_name, audio_key, audio_bytes):
    s3_client.put_object(
        Bucket=bucket_name,
        Key=audio_key,
        Body=audio_bytes,
        ContentType="audio/mpeg",
    )


def generate_samples(
    s3_client,
    polly_client,
    metadata,
    sentences,
    audio_bucket_name,
    sample_counter,
    voice=DEFAULT_VOICE,
    language_code=DEFAULT_LANGUAGE_CODE,
):
    samples = metadata.setdefault("samples", [])
    for sentence in sentences:
        audio_key = f"sample_{sample_counter}.mp3"
        audio_bytes = synthesize_audio(
            polly_client=polly_client,
            text=sentence,
            voice=voice,
            language_code=language_code,
        )
        upload_audio(
            s3_client=s3_client,
            bucket_name=audio_bucket_name,
            audio_key=audio_key,
            audio_bytes=audio_bytes,
        )
        samples.append(
            {
                "id": sample_counter,
                "audio_file": audio_key,
                "characters": sentence,
                "tts_service": DEFAULT_TTS_SERVICE,
                "voice": voice,
            }
        )
        sample_counter += 1
    return metadata


def run_generation(
    tsv_bucket_name=DEFAULT_BUCKET,
    audio_bucket_name=DEFAULT_BUCKET,
    tsv_file_key=DEFAULT_TSV_FILE_KEY,
    metadata_file_key=DEFAULT_METADATA_FILE_KEY,
    sample_counter=None,
    s3_client=None,
    polly_client=None,
):
    s3_client = s3_client or create_boto3_client("s3")
    polly_client = polly_client or create_boto3_client("polly")

    rows = load_tsv_rows(s3_client=s3_client, bucket_name=tsv_bucket_name, key=tsv_file_key)
    sentences = dedupe_sentences(rows)

    metadata = load_metadata(s3_client=s3_client, bucket_name=tsv_bucket_name, key=metadata_file_key)
    if sample_counter is None:
        sample_counter = next_sample_id(metadata)

    updated_metadata = generate_samples(
        s3_client=s3_client,
        polly_client=polly_client,
        metadata=metadata,
        sentences=sentences,
        audio_bucket_name=audio_bucket_name,
        sample_counter=sample_counter,
    )
    write_metadata(
        s3_client=s3_client,
        bucket_name=tsv_bucket_name,
        key=metadata_file_key,
        metadata=updated_metadata,
    )
    return updated_metadata


if __name__ == "__main__":
    run_generation()
