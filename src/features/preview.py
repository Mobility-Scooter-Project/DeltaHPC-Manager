from tkinter import messagebox
import os
import cv2
import random
import atexit
import tempfile
import posixpath

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QSlider, QLabel
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt

import components.menu
import connection

local_temp_path = None

class VideoPlayer(QMainWindow):
    def __init__(self, video_source):
        super().__init__()

        self.setWindowTitle('Video Preview')
        self.setGeometry(100, 100, 800, 600)

        self.video_source = video_source
        self.vid = cv2.VideoCapture(self.video_source)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.video_label = QLabel()
        self.layout.addWidget(self.video_label)

        self.play_button = QPushButton('Play')
        self.play_button.clicked.connect(self.play)
        self.layout.addWidget(self.play_button)

        self.pause_button = QPushButton('Pause')
        self.pause_button.clicked.connect(self.pause)
        self.layout.addWidget(self.pause_button)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(int(self.vid.get(cv2.CAP_PROP_FRAME_COUNT)))
        self.progress_slider.valueChanged.connect(self.set_frame)
        self.layout.addWidget(self.progress_slider)

        self.is_paused = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def play(self):
        self.is_paused = False

    def pause(self):
        self.is_paused = True

    def set_frame(self, position):
        self.vid.set(cv2.CAP_PROP_POS_FRAMES, position)

    def update_frame(self):
        if not self.is_paused:
            ret, frame = self.vid.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(q_img)
                self.video_label.setPixmap(pixmap)
                self.progress_slider.setValue(int(self.vid.get(cv2.CAP_PROP_POS_FRAMES)))
            else:
                self.vid.set(cv2.CAP_PROP_POS_FRAMES, 0)

def cleanup(local_temp_path, remote_temp_path, client):
    """Ensure the cleanup of local and remote temporary files."""
    try:
        # Clean up the remote temporary file
        if remote_temp_path and client:
            client.exec_command(f'rm "{remote_temp_path}"')
            print(f"Remote file {remote_temp_path} deleted.")

        # Clean up the local temporary file
        if local_temp_path and os.path.exists(local_temp_path):
            os.remove(local_temp_path)
            print(f"Local file {local_temp_path} deleted.")

    except Exception as e:
        print(f"Error during cleanup: {e}")

def stream_video_preview(root, remote_file):
    global local_temp_path
    remote_temp_path = None

    try:
        if connection.client is None:
            messagebox.showerror("Preview Error", "Not connected to the server.")
            return

        # Ask the user for the remote path of the video file to preview
        default_path = f"/projects/bddu/data_setup/data"        
        if not remote_file: 
            remote_file = components.menu.open_popup(root, default_path, "Video Preview", "Preview", "Select the remote path of video to preview (root)")
        
        if remote_file == "Cancelled":
            return 

        if remote_file:
            if '.mp4' in remote_file:
                # Define the path for the temporary file on the server
                remote_path = posixpath.join(default_path, remote_file)

                remote_temp_path = posixpath.join("/projects/bddu/data_setup", f"tmp/temp_preview_{random.getrandbits(128)}.mp4")

                # Move current directory to project
                connection.client.exec_command(f"cd {default_path}")

                # Define the ffmpeg command to extract the first 5 seconds
                ffmpeg_cmd = (
                    f'cd {default_path} && export LD_LIBRARY_PATH=/projects/bddu/ffmpeg/lib:$LD_LIBRARY_PATH && '
                    f'/projects/bddu/ffmpeg/bin/ffmpeg -ss 00:00:00 -i "{remote_path}" -t 00:00:05 -c copy "{remote_temp_path}"'
                )

                # Execute the ffmpeg command on the remote server
                stdin, stdout, stderr = connection.client.exec_command(ffmpeg_cmd)
                
                # Wait for the command to finish
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    error_msg = stderr.read().decode()
                    raise Exception(f"FFmpeg error: {error_msg}")
                
                temp_dir = tempfile.gettempdir()  # Get a system-specific temporary directory
                local_temp_path = os.path.join(temp_dir, f"tmp_{random.getrandbits(128)}.mp4")
                
                with open(local_temp_path, 'wb') as file_handle:
                    connection.sftp.getfo(remote_temp_path, file_handle)

                # Remove the temporary file on the remote server
                connection.client.exec_command(f'rm "{remote_temp_path}"')
                
                atexit.register(cleanup, local_temp_path, remote_temp_path, connection.client)

                # Initialize and start the video player
                app = QApplication([])
                player = VideoPlayer(local_temp_path)
                player.show()
                app.exec_()

                # Clean up temporary local file
                os.remove(local_temp_path)
            else:
                messagebox.showerror("Preview Error", f"Cannot preview the file {remote_file}")

    except Exception as e:
        # messagebox.showerror("Preview Error", "Invalid video input")
        print("Preview Error", str(e))
    finally:
        # Cleanup remote file in case of any error
        cleanup(local_temp_path, remote_temp_path, connection.client)