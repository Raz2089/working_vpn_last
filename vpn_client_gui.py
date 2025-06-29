import sys
import time
import subprocess
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QLineEdit, QMessageBox, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import QTimer, Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QMovie, QFont
from PyQt5.QtGui import QIcon



class EmailSender(QThread):
    email_sent = pyqtSignal(bool, str)

    def __init__(self, recipient_email, verification_code):
        super().__init__()
        self.recipient_email = recipient_email
        self.verification_code = verification_code
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = "raz.halali@gmail.com"
        self.sender_password = "klbh sqcu pesx nslb"  # Gmail App Password

    def run(self):
        try:
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = self.recipient_email
            message["Subject"] = "VPN Connection Verification Code"
            body = f"""
            Your VPN verification code is: {self.verification_code}

            This code will expire in 5 minutes.
            """
            message.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.recipient_email, message.as_string())
            server.quit()

            self.email_sent.emit(True, "Verification code sent.")
        except Exception as e:
            self.email_sent.emit(False, f"Email sending failed: {str(e)}")


class VerificationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Email Verification")
        self.setWindowIcon(QIcon("vpn.jpg"))
        self.setFixedSize(350, 220)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border-radius: 12px;
            }
            QLabel {
                font-family: 'Segoe UI';
                font-size: 13px;
                color: #333;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.instruction_label = QLabel("A verification code has been sent to your email.")
        self.instruction_label.setWordWrap(True)
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.instruction_label)

        self.code_label = QLabel("Enter verification code:")
        self.code_label.setAlignment(Qt.AlignLeft)
        self.code_label.setStyleSheet("margin-top: 10px; font-weight: bold;")
        layout.addWidget(self.code_label)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Enter 6-digit code")
        self.code_input.setMaxLength(6)
        self.code_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                border: 1px solid #aaa;
                border-radius: 6px;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
                background-color: #f9fff9;
            }
        """)
        layout.addWidget(self.code_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Verify")
        button_box.button(QDialogButtonBox.Cancel).setText("Cancel")
        button_box.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.timer_label = QLabel("Code expires in: 5:00")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.timer_label)

        self.setLayout(layout)

        self.remaining_time = 300
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)

    def update_countdown(self):
        self.remaining_time -= 1
        minutes = self.remaining_time // 60
        seconds = self.remaining_time % 60
        self.timer_label.setText(f"Code expires in: {minutes}:{seconds:02d}")
        if self.remaining_time <= 0:
            self.countdown_timer.stop()
            QMessageBox.warning(self, "Expired", "Verification code has expired.")
            self.reject()

    def get_code(self):
        return self.code_input.text().strip()


class EmailInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Email Verification")
        self.setWindowIcon(QIcon("vpn.jpg"))
        self.setFixedSize(350, 180)
        self.setModal(True)
        self.setStyleSheet("background-color: white; border-radius: 10px;")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        label = QLabel("Enter your email address to receive a verification code:")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 13px; font-weight: bold; color: #333;")
        layout.addWidget(label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        self.email_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
                background-color: #f9fff9;
            }
        """)
        layout.addWidget(self.email_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Send Code")
        button_box.button(QDialogButtonBox.Cancel).setText("Cancel")
        button_box.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def get_email(self):
        return self.email_input.text().strip()


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VPN Login")
        self.setFixedSize(400, 400)
        self.setWindowIcon(QIcon("vpn.jpg"))
        self.locked = False
        self.attempts = 0
        self.max_attempts = 3
        self.verification_code = None
        self.user_email = None

        self.background = QLabel(self)
        self.background.setGeometry(0, 0, 400, 400)
        self.movie = QMovie("lock.gif")
        self.movie.setScaledSize(QSize(400, 400))
        self.background.setMovie(self.movie)
        self.movie.start()

        self.label = QLabel("Enter Password:")
        self.label.setFont(QFont("Arial", 13, QFont.Bold))
        self.label.setStyleSheet("color: white;")

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(30)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.check_password)
        self.connect_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        self.password_input.setStyleSheet("""
            background-color: rgba(255, 255, 255, 200);
            color: white;
            selection-background-color: #0078d7;
            selection-color: white;
        """)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(self.label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.connect_button)
        layout.addStretch()

        container = QWidget(self)
        container.setLayout(layout)
        container.setGeometry(75, 100, 250, 200)
        container.setStyleSheet("background: transparent;")

    def check_password(self):
        if self.locked:
            QMessageBox.warning(self, "Locked", "Too many failed attempts.")
            return

        password = self.password_input.text()
        if not password.strip():
            QMessageBox.warning(self, "Invalid", "Password cannot be empty.")
            return

        if password == "vpn123":
            self.initiate_email_verification()
        else:
            self.attempts += 1
            if self.attempts >= self.max_attempts:
                self.locked = True
                QMessageBox.critical(self, "Locked", "Too many failed attempts.")
            else:
                QMessageBox.critical(self, "Access Denied",
                                     f"Wrong password. Attempts left: {self.max_attempts - self.attempts}")

    def generate_verification_code(self):
        return ''.join(random.choices(string.digits, k=6))

    def initiate_email_verification(self):
        email_dialog = EmailInputDialog(self)
        if email_dialog.exec_() != QDialog.Accepted:
            return

        self.user_email = email_dialog.get_email()
        if not self.user_email or '@' not in self.user_email:
            QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address.")
            return

        self.verification_code = self.generate_verification_code()
        self.connect_button.setEnabled(False)
        self.connect_button.setText("Sending Code...")

        self.email_sender = EmailSender(self.user_email, self.verification_code)
        self.email_sender.email_sent.connect(self.on_email_sent)
        self.email_sender.start()

    def on_email_sent(self, success, message):
        self.connect_button.setEnabled(True)
        self.connect_button.setText("Connect")

        if not success:
            QMessageBox.critical(self, "Email Error", message)
            return

        verification_dialog = VerificationDialog(self)
        if verification_dialog.exec_() == QDialog.Accepted:
            entered_code = verification_dialog.get_code()
            if entered_code == self.verification_code:
                self.accept_login()
            else:
                QMessageBox.critical(self, "Invalid Code", "Incorrect code entered.")

    def accept_login(self):
        self.close()
        self.vpn_window = VPNClient()
        self.vpn_window.show()


class VPNClient(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("vpn.jpg"))
        self.setWindowTitle("VPN Client GUI")
        self.setFixedSize(400, 400)

        self.vpn_connected = False
        self.start_time = None
        self.client_process = None

        self.background = QLabel(self)
        self.background.setGeometry(0, 0, 400, 400)
        self.movie = QMovie("lock.gif")
        self.movie.setScaledSize(QSize(400, 400))
        self.background.setMovie(self.movie)
        self.movie.start()

        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: red; font-size: 20px; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.ip_label = QLabel("VPN IP: Not Connected")
        self.ip_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        self.ip_label.setAlignment(Qt.AlignCenter)

        self.time_label = QLabel("Time Connected: 00:00:00")
        self.time_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        self.time_label.setAlignment(Qt.AlignCenter)

        self.toggle_button = QPushButton("Turn ON")
        self.toggle_button.clicked.connect(self.toggle_connection)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 6px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #42A5F5;
            }
        """)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time_label)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(self.status_label)
        layout.addWidget(self.ip_label)
        layout.addWidget(self.time_label)
        layout.addWidget(self.toggle_button, alignment=Qt.AlignCenter)
        layout.addStretch()

        self.setLayout(layout)

    def toggle_connection(self):
        self.vpn_connected = not self.vpn_connected
        if self.vpn_connected:
            self.on_connect()
        else:
            self.on_disconnect()

    def on_connect(self):
        try:
            self.client_process = subprocess.Popen([sys.executable, 'encrypted_client_vpn.py'])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start client: {e}")
            self.vpn_connected = False
            return

        self.status_label.setText("Status: Connected")
        self.status_label.setStyleSheet("color: lightgreen; font-size: 20px; font-weight: bold;")
        self.ip_label.setText("VPN IP: 10.100.102.8")
        self.toggle_button.setText("Turn OFF")
        self.start_time = time.time()
        self.timer.start(1000)

    def on_disconnect(self):
        if self.client_process:
            self.client_process.terminate()
            self.client_process.wait()
            self.client_process = None

        self.vpn_connected = False
        self.status_label.setText("Status: Disconnected")
        self.status_label.setStyleSheet("color: red; font-size: 20px; font-weight: bold;")
        self.ip_label.setText("VPN IP: Not Connected")
        self.time_label.setText("Time Connected: 00:00:00")
        self.toggle_button.setText("Turn ON")
        self.timer.stop()

    def update_time_label(self):
        if self.start_time:
            elapsed = int(time.time() - self.start_time)
            h, rem = divmod(elapsed, 3600)
            m, s = divmod(rem, 60)
            self.time_label.setText(f"Time Connected: {h:02}:{m:02}:{s:02}")


def main():
    app = QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
