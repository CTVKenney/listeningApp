#!/usr/bin/env python3

import os
import sys
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import QApplication

THISDIR = os.path.basename(__file__)

def main():
    app = QApplication(sys.argv)
    player = QMediaPlayer()
    media = QMediaContent(QUrl.fromLocalFile(os.path.join(THISDIR, 'sample_1331.mp3')))
    player.setMedia(media)
    player.play()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
