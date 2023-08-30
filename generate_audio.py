#!/usr/bin/env python3

import boto3
import pandas as pd
from io import StringIO
import json

tsv_bucket_name = "chineselisteningpractice"
audio_bucket_name = "chineselisteningpractice"

#Initialize the Amazon S3 and Polly clients
s3 = boto3.client('s3')
polly = boto3.client('polly')

#Download the TSV file from S3 and read its content
tsv_file_key = "ChineseEnglishSentencePairs.tsv"
response = s3.get_object(Bucket=tsv_bucket_name, Key=tsv_file_key)
tsv_content = response['Body'].read().decode('utf-8')

#Read the TSV content into a pandas DataFrame
data = StringIO(tsv_content)
df = pd.read_csv(data, sep = '\t', header = None)

#Drop duplicate Chinese sentences
df.drop_duplicates(subset=1, inplace=True)

#Download the metadata.json file
metadata_file_key = 'metadata.json'
response = s3.get_object(Bucket=tsv_bucket_name, Key=metadata_file_key)
metadata_content = json.loads(response['Body'].read().decode('utf-8'))

#Initialize the sample counter
sample_counter = 2

#Iterate through the DataFrame and generate audio using Amazon Polly
for index, row in df.iterrows():
    chinese_sentence = row[1]

    #Synthesize speech using Amazon Polly
    response = polly.synthesize_speech(
        OutputFormat='mp3',
        Text=chinese_sentence,
        VoiceId='Zhiyu',
        TextType='text',
        LanguageCode='cmn-CN'
    )

    #Save the audio to the audio S3 bucket (in fact, the same)
    audio_key = f'sample_{sample_counter}.mp3'
    s3.put_object(
        Bucket = audio_bucket_name,
        Key = audio_key,
        Body = response['AudioStream'].read(),
        ContentType='audio/mpeg'
    )

    metadata_content['samples'].append({
        'id': sample_counter,
        'audio_file':audio_key,
        'characters':chinese_sentence,
        'tts_service':"polly",
        'voice':'Zhiyu'
    })
    
    #Increment the sample counter
    sample_counter += 1

#Save the updated metadata.json content to the S3 bucket
s3.put_object(
    Bucket=tsv_bucket_name,
    Key=metadata_file_key,
    Body=json.dumps(metadata_content, ensure_ascii=False).encode('utf-8'),
    ContentType='application/json'
)
