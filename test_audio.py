#!/usr/bin/env python3

import sys
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)
    player = QMediaPlayer()
    media = QMediaContent(QUrl.fromLocalFile('/Users/charleskenney/Chinese/listeningApp/sample_1331.mp3'))
    player.setMedia(media)
    player.play()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
