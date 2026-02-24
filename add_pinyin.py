#!/usr/bin/env python3

import json

DEFAULT_BUCKET = "chineselisteningpractice"
DEFAULT_METADATA_KEY = "metadata.json"


def create_s3_client():
    import boto3
    return boto3.client("s3")


def default_pinyin_dependencies():
    from pypinyin import Style, lazy_pinyin
    return lazy_pinyin, Style.TONE


def get_pinyin_pypinyin(characters, lazy_pinyin_fn=None, tone_style=None):
    if lazy_pinyin_fn is None:
        lazy_pinyin_fn, tone_style = default_pinyin_dependencies()
    pinyin_list = lazy_pinyin_fn(characters, style=tone_style)
    return " ".join(pinyin_list).strip()


def load_metadata(s3_client, bucket_name, key):
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    content = response["Body"].read().decode("utf-8")
    return json.loads(content)


def apply_pinyin_to_samples(metadata, lazy_pinyin_fn=None, tone_style=None):
    samples = metadata.get("samples", [])
    for sample in samples:
        characters = sample.get("characters", "")
        sample["pinyin"] = get_pinyin_pypinyin(
            characters=characters,
            lazy_pinyin_fn=lazy_pinyin_fn,
            tone_style=tone_style,
        )
    return metadata


def write_metadata(s3_client, bucket_name, key, metadata):
    metadata_json = json.dumps(metadata, ensure_ascii=False)
    s3_client.put_object(
        Body=metadata_json.encode("utf-8"),
        Bucket=bucket_name,
        Key=key,
        ContentType="application/json",
    )


def update_metadata_in_s3(
    bucket_name=DEFAULT_BUCKET,
    key=DEFAULT_METADATA_KEY,
    s3_client=None,
    lazy_pinyin_fn=None,
    tone_style=None,
):
    s3_client = s3_client or create_s3_client()
    metadata = load_metadata(s3_client=s3_client, bucket_name=bucket_name, key=key)
    updated = apply_pinyin_to_samples(
        metadata=metadata,
        lazy_pinyin_fn=lazy_pinyin_fn,
        tone_style=tone_style,
    )
    write_metadata(s3_client=s3_client, bucket_name=bucket_name, key=key, metadata=updated)
    return updated


if __name__ == "__main__":
    update_metadata_in_s3()
