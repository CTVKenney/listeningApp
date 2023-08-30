#!/usr/bin/env python3

import sys
import os
import atexit
import json
import random
import boto3
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest

os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'coreaudio'


def delete_temp_files():
    for file in os.listdir():
        if file.startswith("downloaded_sample_"):
            os.remove(file)

def download_sample_audio_file(sample):
    session = boto3.Session(
        aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
    )
    s3 = session.client('s3')
    audio_key = sample['audio_file']
    local_filename = f'downloaded_{audio_key}'
    
    with open(local_filename, 'wb') as f:
        s3.download_fileobj('chineselisteningpractice', audio_key, f)

    return local_filename

    print(f'Downloaded {audio_key} to {local_filename}')

class ListeningPracticeApp(QWidget):
    def __init__(self):
        super().__init__()
        

        self.media_player = QMediaPlayer()

        self.setWindowTitle("Chinese Listening Practice")
        self.setGeometry(100, 100, 400, 200)

        self.layout = QVBoxLayout()

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start)
        self.layout.addWidget(self.start_button)

        self.sentence_label = QLabel("")
        self.layout.addWidget(self.sentence_label)
        
#        self.media_player.error.connect(self.handle_media_player_error)
#        self.media_player.stateChanged.connect(self.print_media_player_state)

        self.correct_pinyin_label = QLabel("")
        self.layout.addWidget(self.correct_pinyin_label)

        self.setLayout(self.layout)
        
        self.replay_button = QPushButton('Replay')
        self.replay_button.setEnabled(False)
        self.replay_button.clicked.connect(self.replay)
        self.layout.addWidget(self.replay_button)
        
        self.show_button = QPushButton('Show')
        self.show_button.setEnabled(False)
        self.show_button.clicked.connect(self.show_pinyin)
        self.layout.addWidget(self.show_button)

        self.exit_button = QPushButton('Exit')
        self.exit_button.setEnabled(True)
        self.exit_button.clicked.connect(self.exit_app)
        self.layout.addWidget(self.exit_button)

        self.metadata = None
        self.prev_audio_file = '' 

    def download_metadata(self):
        session = boto3.Session(
            aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
        )
        s3 = session.client('s3')
        response = s3.get_object(Bucket='chineselisteningpractice', Key='metadata.json')
        content = response['Body'].read().decode('utf-8')
        self.metadata = json.loads(content)['samples']

    def start(self):
        if not self.metadata:
            self.download_metadata()

        self.sentence_label.setText('')
        self.correct_pinyin_label.setText('')

        self.sample = random.choice(self.metadata)

        #Download audio file to local file
        local_filename = download_sample_audio_file(self.sample)

        #Play audio file with QMediaPlayer
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(os.path.join(os.getcwd(), local_filename))))
        self.media_player.play()

        #Disable "Start" button
        self.start_button.setEnabled(False)
        
        #Delete the previous audio file if it exists
        if hasattr(self, 'prev_audio_file') and os.path.exists(self.prev_audio_file):
            os.remove(self.prev_audio_file)

        #Store current audio file for deletion later
        self.prev_audio_file = os.path.join(os.getcwd(), local_filename)
        
        self.replay_button.setEnabled(True)
        self.show_button.setEnabled(True)


    def show_pinyin(self):
        correct_pinyin = self.sample["pinyin"]
        self.correct_pinyin_label.setText(correct_pinyin)
        
        #Enable "Start" button
        self.start_button.setEnabled(True)
        
        #Update sentence label
        self.sentence_label.setText(self.sample['characters'])

#    def handle_media_player_error(self):
#        error_msg = self.media_player.errorString()
#        print(f'QMediaPlayer Error: {error_msg}')

    
#    def print_media_player_state(self, state):
#        if state == QMediaPlayer.StoppedState:
#            print("QMediaPlayer state: StoppedState")
#        elif state == QMediaPlayer.PlayingState:
#            print("QMediaPlayer state: PlayingState")
#        elif state == QMediaPlayer.PausedState:
#            print("QMediaPlayer state: PausedState")
#        else:
#            print("QMediaPlayer state: Unknown")

    def replay(self):
        #Stop current playback
        self.media_player.stop()

        #Play audio file again
        file_path = os.path.join(os.getcwd(), self.prev_audio_file)
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
        self.media_player.play()

    def exit_app(self):
        delete_temp_files()
        QApplication.quit()


def delete_temp_files():
    print("Deleting temporary files")
    for file in os.listdir():
        if file.startswith("downloaded_sample_"):
            print(f"Found one file to delete: {file}")
            os.remove(file)
            print("Deleted.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    lp_app = ListeningPracticeApp()
    lp_app.show()
    sys.exit(app.exec())

atexit.register(delete_temp_files)
