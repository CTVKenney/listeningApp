#!/usr/bin/env python3

import sys
import os
import atexit
import json
import random
import boto3
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl

os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'coreaudio'


def delete_temp_files():
    print("Deleting temporary files")
    for file in os.listdir():
        if file.startswith("downloaded_"):
            print(f"Deleting file: {file}")
            os.remove(file)


def download_sample_audio_file(sample):
    # Use default boto3 credential provider chain
    s3 = boto3.client('s3')
    audio_key = sample['audio_file']
    local_filename = f'downloaded_{audio_key}'

    with open(local_filename, 'wb') as f:
        s3.download_fileobj('chineselisteningpractice', audio_key, f)

    return local_filename


class ListeningPracticeApp(QWidget):
    def __init__(self):
        super().__init__()

        self.audio_output = QAudioOutput()
        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)

        self.setWindowTitle("Chinese Listening Practice")
        self.setGeometry(100, 100, 400, 200)

        self.layout = QVBoxLayout()

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start)
        self.layout.addWidget(self.start_button)

        self.sentence_label = QLabel("")
        self.layout.addWidget(self.sentence_label)

        self.correct_pinyin_label = QLabel("")
        self.layout.addWidget(self.correct_pinyin_label)

        self.replay_button = QPushButton('Replay')
        self.replay_button.setEnabled(False)
        self.replay_button.clicked.connect(self.replay)
        self.layout.addWidget(self.replay_button)

        self.show_button = QPushButton('Show')
        self.show_button.setEnabled(False)
        self.show_button.clicked.connect(self.show_pinyin)
        self.layout.addWidget(self.show_button)

        self.exit_button = QPushButton('Exit')
        self.exit_button.clicked.connect(self.exit_app)
        self.layout.addWidget(self.exit_button)

        self.setLayout(self.layout)

        self.metadata = None
        self.prev_audio_file = None

    def download_metadata(self):
        # Use default boto3 credential provider chain
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket='chineselisteningpractice', Key='metadata.json')
        content = response['Body'].read().decode('utf-8')
        self.metadata = json.loads(content)['samples']

    def start(self):
        if not self.metadata:
            self.download_metadata()

        self.sentence_label.clear()
        self.correct_pinyin_label.clear()

        self.sample = random.choice(self.metadata)
        local_filename = download_sample_audio_file(self.sample)

        file_path = os.path.join(os.getcwd(), local_filename)
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.audio_output.setVolume(50)
        self.media_player.play()

        self.start_button.setEnabled(False)
        if self.prev_audio_file and os.path.exists(self.prev_audio_file):
            os.remove(self.prev_audio_file)
        self.prev_audio_file = file_path

        self.replay_button.setEnabled(True)
        self.show_button.setEnabled(True)

    def show_pinyin(self):
        self.correct_pinyin_label.setText(self.sample['pinyin'])
        self.sentence_label.setText(self.sample['characters'])
        self.start_button.setEnabled(True)

    def replay(self):
        self.media_player.stop()
        self.media_player.play()

    def exit_app(self):
        delete_temp_files()
        QApplication.quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    lp_app = ListeningPracticeApp()
    lp_app.show()
    atexit.register(delete_temp_files)
    sys.exit(app.exec())

