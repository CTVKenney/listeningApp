#!/usr/bin/env python3

import boto3
import json
from pypinyin import lazy_pinyin, Style


def get_pinyin_pypinyin(characters):
    pinyin_list = lazy_pinyin(characters, style=Style.TONE)
    pinyin_str = ' '.join(pinyin_list)
    pinyin_str_cleaned = pinyin_str.strip()
    return pinyin_str_cleaned

s3 = boto3.client('s3')

def update_metadata(bucket_name, key):
    response = s3.get_object(Bucket=bucket_name, Key=key)
    content = response['Body'].read().decode('utf-8')
    metadata = json.loads(content)
    samples = metadata['samples']
    for sample in samples:
        characters = sample['characters']
        pinyin_str = get_pinyin_pypinyin(characters)
        sample['pinyin'] = pinyin_str
    metadata_json = json.dumps(metadata, ensure_ascii=False)
    s3.put_object(Body=metadata_json.encode('utf-8'), Bucket=bucket_name, Key=key)

update_metadata('chineselisteningpractice', 'metadata.json')
