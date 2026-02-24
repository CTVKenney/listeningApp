import importlib
import io
import json
import sys
import types
import unittest
from unittest import mock


class _Signal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for callback in list(self._callbacks):
            callback(*args, **kwargs)


class _FakeQWidget:
    def __init__(self):
        self.window_title = None
        self.geometry = None
        self.layout = None

    def setWindowTitle(self, title):
        self.window_title = title

    def setGeometry(self, x, y, width, height):
        self.geometry = (x, y, width, height)

    def setLayout(self, layout):
        self.layout = layout


class _FakeQVBoxLayout:
    def __init__(self):
        self.widgets = []

    def addWidget(self, widget):
        self.widgets.append(widget)


class _FakeQLabel:
    def __init__(self, text=""):
        self._text = text

    def setText(self, text):
        self._text = text

    def clear(self):
        self._text = ""


class _FakeQPushButton:
    def __init__(self, label):
        self.label = label
        self.enabled = True
        self.clicked = _Signal()

    def setEnabled(self, enabled):
        self.enabled = enabled


class _FakeQApplication:
    quit_called = False

    def __init__(self, args):
        self.args = args

    @classmethod
    def quit(cls):
        cls.quit_called = True

    def exec(self):
        return 0


class _FakeQAudioOutput:
    def __init__(self):
        self.volume = None

    def setVolume(self, value):
        self.volume = value


class _FakeQMediaPlayer:
    class MediaStatus:
        EndOfMedia = "end"

    def __init__(self):
        self.audio_output = None
        self.source = None
        self.play_calls = 0
        self.stop_calls = 0
        self.mediaStatusChanged = _Signal()

    def setAudioOutput(self, audio_output):
        self.audio_output = audio_output

    def setSource(self, source):
        self.source = source

    def play(self):
        self.play_calls += 1

    def stop(self):
        self.stop_calls += 1


class _FakeQUrl:
    @staticmethod
    def fromLocalFile(path):
        return f"file://{path}"


def _build_fake_modules():
    pyqt6 = types.ModuleType("PyQt6")
    qt_widgets = types.ModuleType("PyQt6.QtWidgets")
    qt_multimedia = types.ModuleType("PyQt6.QtMultimedia")
    qt_core = types.ModuleType("PyQt6.QtCore")

    qt_widgets.QApplication = _FakeQApplication
    qt_widgets.QWidget = _FakeQWidget
    qt_widgets.QVBoxLayout = _FakeQVBoxLayout
    qt_widgets.QLabel = _FakeQLabel
    qt_widgets.QPushButton = _FakeQPushButton

    qt_multimedia.QMediaPlayer = _FakeQMediaPlayer
    qt_multimedia.QAudioOutput = _FakeQAudioOutput

    qt_core.QUrl = _FakeQUrl

    pyqt6.QtWidgets = qt_widgets
    pyqt6.QtMultimedia = qt_multimedia
    pyqt6.QtCore = qt_core

    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = mock.Mock(name="boto3.client")

    return {
        "PyQt6": pyqt6,
        "PyQt6.QtWidgets": qt_widgets,
        "PyQt6.QtMultimedia": qt_multimedia,
        "PyQt6.QtCore": qt_core,
        "boto3": fake_boto3,
    }


class AppTests(unittest.TestCase):
    def setUp(self):
        fake_modules = _build_fake_modules()
        self.modules_patcher = mock.patch.dict(sys.modules, fake_modules)
        self.modules_patcher.start()

        sys.modules.pop("app", None)
        self.app = importlib.import_module("app")

    def tearDown(self):
        sys.modules.pop("app", None)
        self.modules_patcher.stop()

    def test_delete_temp_files_only_deletes_downloaded_files(self):
        with mock.patch.object(self.app.os, "listdir", return_value=["downloaded_a.mp3", "notes.txt", "downloaded_b.mp3"]), mock.patch.object(
            self.app.os, "remove"
        ) as remove_mock:
            self.app.delete_temp_files()

        remove_mock.assert_has_calls([mock.call("downloaded_a.mp3"), mock.call("downloaded_b.mp3")])
        self.assertEqual(2, remove_mock.call_count)

    def test_download_sample_audio_file_uses_s3_and_returns_local_name(self):
        fake_s3 = mock.Mock()
        self.app.boto3.client.return_value = fake_s3

        with mock.patch("builtins.open", mock.mock_open()) as open_mock:
            local_file = self.app.download_sample_audio_file({"audio_file": "sample_42.mp3"})

        self.assertEqual("downloaded_sample_42.mp3", local_file)
        self.app.boto3.client.assert_called_once_with("s3")
        fake_s3.download_fileobj.assert_called_once()
        self.assertEqual("chineselisteningpractice", fake_s3.download_fileobj.call_args.args[0])
        self.assertEqual("sample_42.mp3", fake_s3.download_fileobj.call_args.args[1])
        open_mock.assert_called_once_with("downloaded_sample_42.mp3", "wb")

    def test_download_metadata_reads_samples_from_s3(self):
        listener = self.app.ListeningPracticeApp()
        fake_s3 = mock.Mock()
        fake_s3.get_object.return_value = {
            "Body": io.BytesIO(json.dumps({"samples": [{"characters": "你好"}]}).encode("utf-8"))
        }
        self.app.boto3.client.return_value = fake_s3

        listener.download_metadata()

        self.assertEqual([{"characters": "你好"}], listener.metadata)
        fake_s3.get_object.assert_called_once_with(Bucket="chineselisteningpractice", Key="metadata.json")

    def test_start_downloads_plays_and_updates_state(self):
        listener = self.app.ListeningPracticeApp()
        sample = {
            "audio_file": "sample_1.mp3",
            "characters": "你好",
            "pinyin": "ni3 hao3",
            "translation": "Hello",
        }
        listener.metadata = [sample]
        listener.sentence_label.setText("old sentence")
        listener.correct_pinyin_label.setText("old pinyin")
        listener.english_label.setText("old english")

        with mock.patch.object(self.app.random, "choice", return_value=sample), mock.patch.object(
            self.app, "download_sample_audio_file", return_value="downloaded_sample_1.mp3"
        ), mock.patch.object(self.app.os, "getcwd", return_value="/tmp/work"), mock.patch.object(
            self.app.os.path, "exists", return_value=False
        ), mock.patch.object(
            self.app.os, "remove"
        ) as remove_mock:
            listener.start()

        self.assertEqual("", listener.sentence_label._text)
        self.assertEqual("", listener.correct_pinyin_label._text)
        self.assertEqual("", listener.english_label._text)
        self.assertEqual("file:///tmp/work/downloaded_sample_1.mp3", listener.media_player.source)
        self.assertEqual(50, listener.audio_output.volume)
        self.assertEqual(1, listener.media_player.play_calls)
        self.assertFalse(listener.start_button.enabled)
        self.assertTrue(listener.replay_button.enabled)
        self.assertTrue(listener.show_button.enabled)
        self.assertFalse(listener.show_english_button.enabled)
        self.assertEqual("/tmp/work/downloaded_sample_1.mp3", listener.prev_audio_file)
        remove_mock.assert_not_called()

    def test_start_downloads_metadata_when_missing(self):
        listener = self.app.ListeningPracticeApp()
        sample = {
            "audio_file": "sample_9.mp3",
            "characters": "再见",
            "pinyin": "zai4 jian4",
        }

        def _load_metadata():
            listener.metadata = [sample]

        with mock.patch.object(listener, "download_metadata", side_effect=_load_metadata) as download_mock, mock.patch.object(
            self.app.random, "choice", return_value=sample
        ), mock.patch.object(self.app, "download_sample_audio_file", return_value="downloaded_sample_9.mp3"), mock.patch.object(
            self.app.os, "getcwd", return_value="/tmp/work"
        ), mock.patch.object(
            self.app.os.path, "exists", return_value=False
        ):
            listener.start()

        download_mock.assert_called_once()

    def test_start_cleans_up_previous_file(self):
        listener = self.app.ListeningPracticeApp()
        sample = {"audio_file": "sample_3.mp3", "characters": "你好", "pinyin": "ni3 hao3"}
        listener.metadata = [sample]
        listener.prev_audio_file = "/tmp/previous.mp3"

        with mock.patch.object(self.app.random, "choice", return_value=sample), mock.patch.object(
            self.app, "download_sample_audio_file", return_value="downloaded_sample_3.mp3"
        ), mock.patch.object(self.app.os, "getcwd", return_value="/tmp/work"), mock.patch.object(
            self.app.os.path, "exists", return_value=True
        ), mock.patch.object(
            self.app.os, "remove"
        ) as remove_mock:
            listener.start()

        remove_mock.assert_called_once_with("/tmp/previous.mp3")

    def test_show_pinyin_updates_labels_and_buttons(self):
        listener = self.app.ListeningPracticeApp()
        listener.sample = {"characters": "你好", "pinyin": "ni3 hao3"}
        listener.start_button.setEnabled(False)
        listener.show_english_button.setEnabled(False)

        listener.show_pinyin()

        self.assertEqual("你好", listener.sentence_label._text)
        self.assertEqual("ni3 hao3", listener.correct_pinyin_label._text)
        self.assertTrue(listener.start_button.enabled)
        self.assertTrue(listener.show_english_button.enabled)

    def test_show_english_uses_translation_and_disables_button(self):
        listener = self.app.ListeningPracticeApp()
        listener.sample = {"translation": "If you have trouble, call me."}
        listener.show_english_button.setEnabled(True)

        listener.show_english()

        self.assertEqual("If you have trouble, call me.", listener.english_label._text)
        self.assertFalse(listener.show_english_button.enabled)

    def test_show_english_handles_missing_translation(self):
        listener = self.app.ListeningPracticeApp()
        listener.sample = {}

        listener.show_english()

        self.assertEqual("", listener.english_label._text)

    def test_replay_stops_then_plays(self):
        listener = self.app.ListeningPracticeApp()

        listener.replay()

        self.assertEqual(1, listener.media_player.stop_calls)
        self.assertEqual(1, listener.media_player.play_calls)

    def test_exit_app_cleans_up_and_quits(self):
        listener = self.app.ListeningPracticeApp()

        with mock.patch.object(self.app, "delete_temp_files") as cleanup_mock, mock.patch.object(
            self.app.QApplication, "quit"
        ) as quit_mock:
            listener.exit_app()

        cleanup_mock.assert_called_once_with()
        quit_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
