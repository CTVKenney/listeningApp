import io
import json
import unittest
from unittest import mock

import add_pinyin


class GetPinyinTests(unittest.TestCase):
    def test_get_pinyin_uses_injected_dependencies(self):
        lazy_pinyin_fn = mock.Mock(return_value=["ni3", "hao3"])

        result = add_pinyin.get_pinyin_pypinyin(
            "你好", lazy_pinyin_fn=lazy_pinyin_fn, tone_style="STYLE"
        )

        self.assertEqual("ni3 hao3", result)
        lazy_pinyin_fn.assert_called_once_with("你好", style="STYLE")

    def test_get_pinyin_uses_default_dependencies_when_not_injected(self):
        lazy_pinyin_fn = mock.Mock(return_value=["ce4", "shi4"])
        with mock.patch.object(
            add_pinyin,
            "default_pinyin_dependencies",
            return_value=(lazy_pinyin_fn, "TONE"),
        ):
            result = add_pinyin.get_pinyin_pypinyin("测试")

        self.assertEqual("ce4 shi4", result)
        lazy_pinyin_fn.assert_called_once_with("测试", style="TONE")


class MetadataTransformTests(unittest.TestCase):
    def test_apply_pinyin_to_samples_updates_each_sample(self):
        metadata = {
            "samples": [
                {"characters": "你好"},
                {"characters": "再见"},
            ]
        }

        def fake_lazy_pinyin(text, style):
            return [f"{text}-{style}"]

        updated = add_pinyin.apply_pinyin_to_samples(
            metadata=metadata,
            lazy_pinyin_fn=fake_lazy_pinyin,
            tone_style="STYLE",
        )

        self.assertIs(updated, metadata)
        self.assertEqual("你好-STYLE", updated["samples"][0]["pinyin"])
        self.assertEqual("再见-STYLE", updated["samples"][1]["pinyin"])

    def test_apply_pinyin_to_samples_handles_missing_samples(self):
        metadata = {}

        updated = add_pinyin.apply_pinyin_to_samples(
            metadata=metadata,
            lazy_pinyin_fn=lambda text, style: ["x"],
            tone_style="STYLE",
        )

        self.assertEqual({}, updated)


class S3FlowTests(unittest.TestCase):
    def test_load_metadata_decodes_json(self):
        s3_client = mock.Mock()
        payload = {"samples": [{"characters": "你好"}]}
        s3_client.get_object.return_value = {
            "Body": io.BytesIO(json.dumps(payload).encode("utf-8"))
        }

        metadata = add_pinyin.load_metadata(s3_client, "bucket", "metadata.json")

        self.assertEqual(payload, metadata)
        s3_client.get_object.assert_called_once_with(Bucket="bucket", Key="metadata.json")

    def test_write_metadata_uploads_json(self):
        s3_client = mock.Mock()
        payload = {"samples": [{"characters": "你好", "pinyin": "ni3 hao3"}]}

        add_pinyin.write_metadata(s3_client, "bucket", "metadata.json", payload)

        s3_client.put_object.assert_called_once()
        kwargs = s3_client.put_object.call_args.kwargs
        self.assertEqual("bucket", kwargs["Bucket"])
        self.assertEqual("metadata.json", kwargs["Key"])
        self.assertEqual("application/json", kwargs["ContentType"])
        uploaded = json.loads(kwargs["Body"].decode("utf-8"))
        self.assertEqual(payload, uploaded)

    def test_update_metadata_in_s3_runs_end_to_end_with_mocks(self):
        s3_client = mock.Mock()
        s3_client.get_object.return_value = {
            "Body": io.BytesIO(
                json.dumps({"samples": [{"characters": "你好"}, {"characters": "再见"}]}).encode("utf-8")
            )
        }
        lazy_pinyin_fn = mock.Mock(side_effect=[["ni3", "hao3"], ["zai4", "jian4"]])

        result = add_pinyin.update_metadata_in_s3(
            bucket_name="bucket",
            key="metadata.json",
            s3_client=s3_client,
            lazy_pinyin_fn=lazy_pinyin_fn,
            tone_style="STYLE",
        )

        self.assertEqual("ni3 hao3", result["samples"][0]["pinyin"])
        self.assertEqual("zai4 jian4", result["samples"][1]["pinyin"])
        self.assertEqual(2, lazy_pinyin_fn.call_count)
        s3_client.put_object.assert_called_once()


if __name__ == "__main__":
    unittest.main()
