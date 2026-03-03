import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QTextEdit, QLineEdit, QPushButton, QFileDialog,
                             QMessageBox, QLabel, QFrame, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QFont, QIcon, QPalette, QColor

import api_client

# ---- Caminho dos assets ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ROBOT_IMG = os.path.join(ASSETS_DIR, "robo.png")


class WorkerThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, action, *args):
        super().__init__()
        self.action = action
        self.args = args

    def run(self):
        try:
            if self.action == "chat":
                resp = api_client.send_message(self.args[0])
                self.finished.emit(resp)
            elif self.action == "upload":
                resp = api_client.upload_document(self.args[0])
                self.finished.emit(resp)
            elif self.action == "upload_url":
                resp = api_client.index_url(self.args[0])
                self.finished.emit(resp)
        except Exception as e:
            self.finished.emit(f"Erro interno no aplicativo: {str(e)}")


# ---- Paleta de Cores ----
COLORS = {
    "bg_dark":       "#0d1117",
    "bg_card":       "#161b22",
    "bg_input":      "#0d1117",
    "accent":        "#00c853",
    "accent_hover":  "#00e676",
    "text_primary":  "#ffffff",
    "text_secondary":"#b0b0b0",
    "text_user":     "#56d364",
    "text_ai":       "#7ee787",
    "text_system":   "#b0b0b0",
    "border":        "#1a3a1a",
    "danger":        "#ff6b6b",
    "success":       "#00c853",
}

GLOBAL_STYLE = f"""
    QMainWindow {{
        background-color: {COLORS['bg_dark']};
    }}
    QWidget#centralWidget {{
        background-color: {COLORS['bg_dark']};
    }}
    QTextEdit#chatHistory {{
        background-color: {COLORS['bg_card']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 16px;
        font-size: 14px;
        font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
        selection-background-color: {COLORS['accent']};
    }}
    QLineEdit#inputField {{
        background-color: {COLORS['bg_input']};
        color: {COLORS['text_primary']};
        border: 2px solid {COLORS['border']};
        border-radius: 20px;
        padding: 10px 18px;
        font-size: 14px;
        font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
    }}
    QLineEdit#inputField:focus {{
        border-color: {COLORS['accent']};
    }}
    QPushButton#btnSend {{
        background-color: {COLORS['accent']};
        color: white;
        border: none;
        border-radius: 20px;
        padding: 10px 24px;
        font-size: 14px;
        font-weight: bold;
        font-family: 'Segoe UI', sans-serif;
    }}
    QPushButton#btnSend:hover {{
        background-color: {COLORS['accent_hover']};
    }}
    QPushButton#btnSend:disabled {{
        background-color: {COLORS['border']};
        color: {COLORS['text_secondary']};
    }}
    QPushButton#btnUpload {{
        background-color: transparent;
        color: {COLORS['text_secondary']};
        border: 2px solid {COLORS['border']};
        border-radius: 20px;
        padding: 10px 16px;
        font-size: 13px;
        font-family: 'Segoe UI', sans-serif;
    }}
    QPushButton#btnUpload:hover {{
        border-color: {COLORS['accent']};
        color: {COLORS['accent']};
    }}
    QLabel#headerTitle {{
        color: {COLORS['text_primary']};
        font-size: 20px;
        font-weight: bold;
        font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
    }}
    QLabel#headerSubtitle {{
        color: {COLORS['text_secondary']};
        font-size: 12px;
        font-family: 'Segoe UI', sans-serif;
    }}
    QFrame#headerFrame {{
        background-color: {COLORS['bg_card']};
        border-bottom: 1px solid {COLORS['border']};
        border-radius: 0px;
    }}
    QFrame#inputFrame {{
        background-color: {COLORS['bg_card']};
        border-top: 1px solid {COLORS['border']};
        border-radius: 0px;
    }}
"""


class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instarzinho (Jurídico)")
        self.resize(900, 700)
        self.setMinimumSize(600, 400)

        # Ícone da janela
        if os.path.exists(ROBOT_IMG):
            self.setWindowIcon(QIcon(ROBOT_IMG))

        self.setStyleSheet(GLOBAL_STYLE)
        self.initUI()

    def initUI(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== HEADER =====
        header = QFrame()
        header.setObjectName("headerFrame")
        header.setFixedHeight(70)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)

        # Logo do robô no header
        if os.path.exists(ROBOT_IMG):
            logo_label = QLabel()
            pixmap = QPixmap(ROBOT_IMG).scaled(
                QSize(44, 44), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(pixmap)
            header_layout.addWidget(logo_label)

        # Texto do header
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title_label = QLabel("Instarzinho (Jurídico)")
        title_label.setObjectName("headerTitle")
        title_layout.addWidget(title_label)

        subtitle = QLabel("Assistente IA • Conectado ao Servidor")
        subtitle.setObjectName("headerSubtitle")
        title_layout.addWidget(subtitle)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # Status indicator
        status_dot = QLabel("🟢")
        status_dot.setStyleSheet("font-size: 10px;")
        header_layout.addWidget(status_dot)

        main_layout.addWidget(header)

        # ===== CHAT AREA =====
        chat_container = QWidget()
        chat_container.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(16, 12, 16, 12)

        # Container com imagem de fundo
        self.chat_stack = QWidget()
        stack_layout = QVBoxLayout(self.chat_stack)
        stack_layout.setContentsMargins(0, 0, 0, 0)

        self.chat_history = QTextEdit()
        self.chat_history.setObjectName("chatHistory")
        self.chat_history.setReadOnly(True)
        # Fundo transparente para mostrar a marca d'água
        self.chat_history.setStyleSheet(
            self.chat_history.styleSheet() + """
            QTextEdit#chatHistory {
                background-color: transparent;
            }
        """)
        stack_layout.addWidget(self.chat_history)

        # Marca d'água (robo.png como background translúcido)
        self.bg_label = QLabel(self.chat_stack)
        if os.path.exists(ROBOT_IMG):
            bg_pixmap = QPixmap(ROBOT_IMG)
            self.bg_label.setPixmap(bg_pixmap)
            self.bg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.bg_label.setScaledContents(False)
            opacity = QGraphicsOpacityEffect()
            opacity.setOpacity(0.12)
            self.bg_label.setGraphicsEffect(opacity)
            self.bg_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.bg_label.setStyleSheet("background: transparent;")
            self.bg_label.lower()  # Manda pra trás do QTextEdit

        chat_layout.addWidget(self.chat_stack)

        main_layout.addWidget(chat_container, 1)

        # ===== INPUT BAR =====
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_frame.setFixedHeight(70)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 12, 16, 12)
        input_layout.setSpacing(10)

        self.btn_upload = QPushButton("📎 Anexar")
        self.btn_upload.setObjectName("btnUpload")
        self.btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_upload.clicked.connect(self.browse_file)
        input_layout.addWidget(self.btn_upload)

        self.input_field = QLineEdit()
        self.input_field.setObjectName("inputField")
        self.input_field.setPlaceholderText("Digite sua mensagem...")
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field, 1)

        self.btn_send = QPushButton("Enviar ➤")
        self.btn_send.setObjectName("btnSend")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self.send_message)
        input_layout.addWidget(self.btn_send)

        main_layout.addWidget(input_frame)

        # Mensagem de boas-vindas
        self.show_welcome()

    def resizeEvent(self, event):
        """Redimensiona a marca d'água ao redimensionar a janela."""
        super().resizeEvent(event)
        if hasattr(self, 'bg_label') and hasattr(self, 'chat_history'):
            # Centraliza o robo.png ocupando a área do chat
            chat_rect = self.chat_history.geometry()
            if os.path.exists(ROBOT_IMG):
                pix = QPixmap(ROBOT_IMG).scaled(
                    QSize(min(chat_rect.width() - 40, 350), min(chat_rect.height() - 40, 350)),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.bg_label.setPixmap(pix)
                lbl_x = chat_rect.x() + (chat_rect.width() - pix.width()) // 2
                lbl_y = chat_rect.y() + (chat_rect.height() - pix.height()) // 2
                self.bg_label.setGeometry(lbl_x, lbl_y, pix.width(), pix.height())

    def show_welcome(self):
        welcome_html = f"""
        <div style='text-align: center; padding: 30px;'>
            <p style='color: {COLORS["text_secondary"]}; font-size: 14px; margin-top: 10px;'>
                Bem-vindo ao <b style='color: {COLORS["accent"]};'>Instarzinho (Jurídico)</b>!
            </p>
            <p style='color: {COLORS["text_secondary"]}; font-size: 13px;'>
                Faça perguntas sobre os dados da planilha ou envie documentos para análise.
            </p>
        </div>
        """
        self.chat_history.setHtml(welcome_html)

    # ---- Métodos de mensagem ----

    def append_system_message(self, text):
        html = (
            f"<div style='margin: 6px 0; padding: 8px 14px; "
            f"background-color: #1c2a4a; border-left: 3px solid #555; "
            f"border-radius: 6px;'>"
            f"<span style='color: #999; font-size: 12px;'>⚙️ Sistema</span><br>"
            f"<span style='color: #b0b0b0; font-size: 13px;'>{text}</span>"
            f"</div>"
        )
        self.chat_history.append(html)

    def append_user_message(self, text):
        html = (
            f"<div style='margin: 8px 0; padding: 10px 16px; "
            f"background-color: #0a2647; border-radius: 12px; "
            f"border: 1px solid {COLORS['border']};'>"
            f"<span style='color: #ffffff; font-size: 12px; font-weight: bold;'>👤 Você</span><br>"
            f"<span style='color: {COLORS['text_user']}; font-size: 14px;'>{text}</span>"
            f"</div>"
        )
        self.chat_history.append(html)

    def append_ai_message(self, text):
        # Processa quebras de linha para HTML
        formatted = text.replace('\\n', '<br>').replace('\n', '<br>')
        # Garante que tags <b> herdem a cor verde
        formatted = formatted.replace('<b>', f"<b style='color:{COLORS['accent']};'>")
        html = (
            f"<div style='margin: 8px 0; padding: 12px 16px; "
            f"background-color: #112240; border-radius: 12px; "
            f"border: 1px solid {COLORS['border']};'>"
            f"<span style='color: #ffffff; font-size: 12px; font-weight: bold;'>🤖 Instarzinho IA</span><br><br>"
            f"<span style='color: {COLORS['text_ai']}; font-size: 14px;'>{formatted}</span>"
            f"</div>"
        )
        self.chat_history.append(html)

    # ---- Ações ----

    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return

        self.input_field.clear()
        self.append_user_message(text)

        if text.startswith("/indexar"):
            self.append_system_message("Para indexar, use o botão <b>📎 Anexar</b>.")
            return

        self.set_input_enabled(False)
        self.append_system_message("Processando sua pergunta... aguarde a resposta da IA.")

        self.thread = WorkerThread("chat", text)
        self.thread.finished.connect(self.on_chat_response)
        self.thread.start()

    def browse_file(self):
        text = self.input_field.text().strip()

        if text.startswith("http") and "docs.google.com/spreadsheets" in text:
            self.input_field.clear()
            self.set_input_enabled(False)
            self.append_system_message(f"Enviando URL da planilha para o servidor indexar...")
            self.thread = WorkerThread("upload_url", text)
            self.thread.finished.connect(self.on_upload_response)
            self.thread.start()
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione um documento para a IA ler",
            "",
            "Documentos (*.pdf *.docx *.csv *.xlsx)"
        )
        if file_path:
            self.set_input_enabled(False)
            self.append_system_message(
                f"Enviando <b>{os.path.basename(file_path)}</b> para indexação..."
            )
            self.thread = WorkerThread("upload", file_path)
            self.thread.finished.connect(self.on_upload_response)
            self.thread.start()

    def on_chat_response(self, response_text):
        self.append_ai_message(response_text)
        self.set_input_enabled(True)
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )

    def on_upload_response(self, response_text):
        self.append_system_message(response_text)
        self.set_input_enabled(True)

    def set_input_enabled(self, enabled):
        self.btn_send.setEnabled(enabled)
        self.btn_upload.setEnabled(enabled)
        self.input_field.setEnabled(enabled)
        if enabled:
            self.input_field.setFocus()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark Palette global
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLORS["bg_dark"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(COLORS["bg_card"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(COLORS["bg_input"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLORS["accent"]))
    app.setPalette(palette)

    window = ChatWindow()
    window.show()
    sys.exit(app.exec())
