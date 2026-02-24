import io
import json
import unittest
from unittest import mock

import generate_audio


class TsvProcessingTests(unittest.TestCase):
    def test_load_tsv_rows_reads_rows_and_skips_short_rows(self):
        s3_client = mock.Mock()
        # Starts with BOM to validate utf-8-sig decoding.
        tsv_data = "\ufeff1\t你好\t1\tHello\n2\t再见\t2\tBye\nmalformed-only\n"
        s3_client.get_object.return_value = {"Body": io.BytesIO(tsv_data.encode("utf-8"))}

        rows = generate_audio.load_tsv_rows(s3_client, "bucket", "pairs.tsv")

        self.assertEqual(["1", "你好", "1", "Hello"], rows[0])
        self.assertEqual(["2", "再见", "2", "Bye"], rows[1])
        self.assertEqual(2, len(rows))

    def test_dedupe_sentences_removes_duplicates_and_blanks(self):
        rows = [
            ["1", "你好", "1", "Hello"],
            ["2", "你好", "2", "Hello again"],
            ["3", "", "3", "Empty"],
            ["4", "再见", "4", "Bye"],
        ]

        deduped = generate_audio.dedupe_sentences(rows)

        self.assertEqual(["你好", "再见"], deduped)


class MetadataTests(unittest.TestCase):
    def test_next_sample_id_uses_max_existing_id(self):
        metadata = {"samples": [{"id": 4}, {"id": 19}, {"id": 7}, {"id": "not-int"}]}

        next_id = generate_audio.next_sample_id(metadata)

        self.assertEqual(20, next_id)

    def test_next_sample_id_honors_minimum_start(self):
        metadata = {"samples": []}

        next_id = generate_audio.next_sample_id(metadata, minimum_start=10)

        self.assertEqual(10, next_id)


class PollyAndS3Tests(unittest.TestCase):
    def test_synthesize_audio_reads_audio_stream(self):
        polly_client = mock.Mock()
        polly_client.synthesize_speech.return_value = {"AudioStream": io.BytesIO(b"mp3-data")}

        audio = generate_audio.synthesize_audio(polly_client, text="你好", voice="Zhiyu")

        self.assertEqual(b"mp3-data", audio)
        polly_client.synthesize_speech.assert_called_once_with(
            OutputFormat="mp3",
            Text="你好",
            VoiceId="Zhiyu",
            TextType="text",
            LanguageCode="cmn-CN",
        )

    def test_generate_samples_uploads_audio_and_updates_metadata(self):
        s3_client = mock.Mock()
        polly_client = mock.Mock()
        polly_client.synthesize_speech.side_effect = [
            {"AudioStream": io.BytesIO(b"audio-1")},
            {"AudioStream": io.BytesIO(b"audio-2")},
        ]
        metadata = {"samples": []}

        updated = generate_audio.generate_samples(
            s3_client=s3_client,
            polly_client=polly_client,
            metadata=metadata,
            sentences=["你好", "再见"],
            audio_bucket_name="audio-bucket",
            sample_counter=2,
            voice="Zhiyu",
        )

        self.assertIs(updated, metadata)
        self.assertEqual(2, len(updated["samples"]))
        self.assertEqual(2, updated["samples"][0]["id"])
        self.assertEqual("sample_2.mp3", updated["samples"][0]["audio_file"])
        self.assertEqual("你好", updated["samples"][0]["characters"])
        self.assertEqual(3, updated["samples"][1]["id"])
        self.assertEqual(2, s3_client.put_object.call_count)

        first_upload = s3_client.put_object.call_args_list[0].kwargs
        self.assertEqual("audio-bucket", first_upload["Bucket"])
        self.assertEqual("sample_2.mp3", first_upload["Key"])
        self.assertEqual(b"audio-1", first_upload["Body"])
        self.assertEqual("audio/mpeg", first_upload["ContentType"])


class EndToEndOrchestrationTests(unittest.TestCase):
    def test_run_generation_orchestrates_calls_and_writes_metadata(self):
        s3_client = mock.Mock()
        polly_client = mock.Mock()

        tsv_data = "1\t你好\t1\tHello\n2\t你好\t2\tHello-again\n3\t再见\t3\tBye\n"
        existing_metadata = {"samples": [{"id": 5, "audio_file": "sample_5.mp3", "characters": "旧"}]}

        s3_client.get_object.side_effect = [
            {"Body": io.BytesIO(tsv_data.encode("utf-8"))},
            {"Body": io.BytesIO(json.dumps(existing_metadata).encode("utf-8"))},
        ]
        polly_client.synthesize_speech.side_effect = [
            {"AudioStream": io.BytesIO(b"audio-6")},
            {"AudioStream": io.BytesIO(b"audio-7")},
        ]

        updated = generate_audio.run_generation(
            tsv_bucket_name="content-bucket",
            audio_bucket_name="audio-bucket",
            tsv_file_key="pairs.tsv",
            metadata_file_key="metadata.json",
            s3_client=s3_client,
            polly_client=polly_client,
        )

        self.assertEqual(3, len(updated["samples"]))
        new_entries = updated["samples"][1:]
        self.assertEqual(6, new_entries[0]["id"])
        self.assertEqual("你好", new_entries[0]["characters"])
        self.assertEqual(7, new_entries[1]["id"])
        self.assertEqual("再见", new_entries[1]["characters"])

        self.assertEqual(3, s3_client.put_object.call_count)
        metadata_write = s3_client.put_object.call_args_list[-1].kwargs
        self.assertEqual("content-bucket", metadata_write["Bucket"])
        self.assertEqual("metadata.json", metadata_write["Key"])
        self.assertEqual("application/json", metadata_write["ContentType"])

        saved_metadata = json.loads(metadata_write["Body"].decode("utf-8"))
        self.assertEqual(updated, saved_metadata)

    def test_run_generation_respects_explicit_sample_counter(self):
        s3_client = mock.Mock()
        polly_client = mock.Mock()

        s3_client.get_object.side_effect = [
            {"Body": io.BytesIO("1\t你好\t1\tHello\n".encode("utf-8"))},
            {"Body": io.BytesIO(json.dumps({"samples": [{"id": 99}]}).encode("utf-8"))},
        ]
        polly_client.synthesize_speech.return_value = {"AudioStream": io.BytesIO(b"audio")}

        updated = generate_audio.run_generation(
            tsv_bucket_name="content-bucket",
            audio_bucket_name="audio-bucket",
            tsv_file_key="pairs.tsv",
            metadata_file_key="metadata.json",
            sample_counter=2,
            s3_client=s3_client,
            polly_client=polly_client,
        )

        self.assertEqual(2, updated["samples"][1]["id"])


if __name__ == "__main__":
    unittest.main()
