#!/usr/bin/env python3

import os
import sys
from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import QApplication

THISDIR = os.path.dirname(__file__)

def main():
    app = QApplication(sys.argv)

    audio_output = QAudioOutput()
    player = QMediaPlayer()
    player.setAudioOutput(audio_output)

    media = QUrl.fromLocalFile(os.path.join(THISDIR, "sample_1331.mp3"))
    player.setSource(media)
    audio_output.setVolume(50)
    player.play()

    # Automatically quit once playback finishes
    player.mediaStatusChanged.connect(
        lambda status: app.quit() if status == QMediaPlayer.MediaStatus.EndOfMedia else None
    )

    sys.exit(app.exec())

if __name__ == '__main__':
    main()

