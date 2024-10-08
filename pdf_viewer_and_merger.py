import sys
import os
import fitz  # PyMuPDF

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QMessageBox,
    QVBoxLayout, QWidget, QScrollArea, QHBoxLayout, QProgressBar
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QPainter, QColor

class CapsuleProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(0)
        self.setMaximum(100)
        self.text = ""

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw the black block
        rect_width = 60
        rect_height = 20
        rect_x = (self.width() - rect_width) / 2
        rect_y = (self.height() - rect_height) / 2
        painter.fillRect(rect_x, rect_y, rect_width, rect_height, QColor("#222"))

        # Draw the text (percentage)
        painter.setPen(Qt.white)
        painter.setFont(self.font())
        text_rect = painter.fontMetrics().boundingRect(self.text)
        text_x = rect_x + (rect_width - text_rect.width()) / 2
        text_y = rect_y + (rect_height - text_rect.height()) / 2 + text_rect.height()
        painter.drawText(text_x, text_y, self.text)

class PDFViewerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.input_pdf = None  # Initialize input_pdf attribute
        self.output_pdf = None  # Initialize output_pdf attribute
        self.current_page = 0  # Current page index
        self.total_pages = 0  # Total number of pages
        self.initUI()

    def initUI(self):
        self.setWindowTitle('PDF Viewer and Merger')
        self.setGeometry(100, 100, 1200, 600)  # Increased width to 1200

        # Main widget and layout
        main_widget = DropWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Left side layout (for PDF display and controls)
        display_widget = QWidget(self)
        display_layout = QVBoxLayout(display_widget)

         # Hint label for drag and drop
        self.hint_label = QLabel("Drag and drop a PDF file here or click 'Open PDF' to upload.", self)
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("color: #888; font-size: 14px; padding: 20px;")
        display_layout.addWidget(self.hint_label)  # Add hint label to the display layout

        # Scroll area for Input PDF pages
        self.scroll_area = QScrollArea(self)
        display_layout.addWidget(self.scroll_area)

        # Widget to hold Input PDF pages
        self.scroll_widget = QWidget(self.scroll_area)
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_widget)

        main_layout.addWidget(display_widget)

        # File path and page indicator layout
        file_page_layout = QHBoxLayout()
        file_page_layout.setContentsMargins(10, 0, 10, 0)

        # File path label
        self.file_path_label = QLabel(self)
        self.file_path_label.setStyleSheet("color: #555; font-size: 12px;")
        file_page_layout.addWidget(self.file_path_label)

        # Page indicator label
        self.page_indicator_label = QLabel(self)
        self.page_indicator_label.setStyleSheet("color: #555; font-size: 12px; margin-left: auto;")
        file_page_layout.addWidget(self.page_indicator_label)

        display_layout.addLayout(file_page_layout)

        # Progress bar (Capsule shaped)
        self.loading_bar = CapsuleProgressBar(self)
        self.loading_bar.setStyleSheet(
            """
            QProgressBar {
                border: none;
                background-color: #f0f0f0;
                height: 10px;
                border-radius: 5px;
                margin-bottom: 5px;
            }
            """
        )
        display_layout.addWidget(self.loading_bar, alignment=Qt.AlignBottom)
        self.loading_bar.hide()  # Initially hide the progress bar

        main_layout.addWidget(display_widget)

        # Right side layout (for buttons)
        button_widget = QWidget(self)
        button_widget.setStyleSheet(
            """
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            """
        )
        button_layout = QVBoxLayout(button_widget)

        def create_button(text, clicked_slot):
            button = QPushButton(text)
            button.setMinimumSize(QSize(180, 40))
            button.setStyleSheet(
                """
                QPushButton {
                    background-color: #f0f0f0;
                    color: #555;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 16px;
                    margin-bottom: 10px;
                }
                QPushButton:hover {
                    background-color: #007bff;
                    border-color: #007bff;
                    color: white;
                }
                """
            )
            button.clicked.connect(clicked_slot)
            button_layout.addWidget(button)

        # Open PDF button (first button)
        create_button('Open PDF', self.open_pdf)

        # Merge Vertically and Horizontally buttons
        create_button('Merge Vertically', lambda: self.merge_button_clicked(2, horizontal=False))
        create_button('Merge Horizontally', lambda: self.merge_button_clicked(2, horizontal=True))


        # Open Folder button (last button)
        self.open_folder_btn = QPushButton('Open Folder', self)
        self.open_folder_btn.setMinimumSize(QSize(180, 40))
        self.open_folder_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f0f0f0;
                color: #555;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 10px;
                font-size: 16px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #007bff;
                border-color: #007bff;
                color: white;
            }
            """
        )
        self.open_folder_btn.clicked.connect(self.open_folder)
        button_layout.addWidget(self.open_folder_btn)

        main_layout.addWidget(button_widget)

    def open_pdf(self):
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("PDF files (*.pdf)")
        if file_dialog.exec_():
            filenames = file_dialog.selectedFiles()
            for filename in filenames:
                self.input_pdf = filename  # Set input_pdf attribute
                self.load_pdf(filename)

    def load_pdf(self, filename):
        self.file_path_label.setText(f'File: {filename}')
        self.pdf_document = fitz.open(filename)
        self.total_pages = len(self.pdf_document)
        self.current_page = 0
        self.update_page_indicator()
        self.display_pdf()

    def display_pdf(self):
        # Clear previous widgets from scroll layout
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if self.pdf_document:
            for page_num in range(len(self.pdf_document)):
                page = self.pdf_document.load_page(page_num)
                pixmap = self.render_page(page)
                label = QLabel()
                label.setPixmap(pixmap)
                self.scroll_layout.addWidget(label)
            self.update_page_indicator()

    def render_page(self, page):
        mat = fitz.Matrix(1, 1)
        pixmap = page.get_pixmap(matrix=mat)
        image = QPixmap()
        image.loadFromData(pixmap.tobytes())
        return image

    def merge_button_clicked(self, page_count, horizontal=True):
        if self.input_pdf:
            self.output_pdf = self.get_output_filename()
            if self.output_pdf:
                if self.input_pdf == self.output_pdf:
                    QMessageBox.critical(self, "Error", "Input and output files must be different.")
                    return

                try:
                    if horizontal:
                        self.merge_two_pages_horizontally(self.output_pdf)
                    else:
                        self.merge_two_pages_vertically(self.output_pdf, page_count)

                    print(f'PDF merged and saved to {self.output_pdf}')
                    if os.path.exists(self.output_pdf):
                        self.load_pdf(self.output_pdf)  # Reload the new PDF to display
                    else:
                        QMessageBox.critical(self, "Error", f"Failed to save merged PDF to:\n{self.output_pdf}")

                except Exception as e:
                    print(f'Error: {e}')
                    QMessageBox.critical(self, "Error", f"Error merging PDF:\n{e}")

        else:
            QMessageBox.warning(self, "No PDF Selected", "Please select a PDF file.")

    def merge_two_pages_horizontally(self, output_pdf):
        pdf_writer = fitz.open()
        pdf_document = fitz.open(self.input_pdf)
        num_pages = len(pdf_document)

        try:
            for i in range(0, num_pages, 2):
                page1 = pdf_document[i]
                page2 = pdf_document[i + 1] if i + 1 < num_pages else None

                merged_page_width = page1.rect.width + (page2.rect.width if page2 else 0)
                merged_page_height = max(page1.rect.height, page2.rect.height if page2 else 0)

                merged_page = pdf_writer.new_page(width=merged_page_width, height=merged_page_height)
                draw_pdf_page(merged_page, page1, 0, 0)
                if page2:
                    draw_pdf_page(merged_page, page2, page1.rect.width, 0)

            pdf_writer.save(output_pdf)
            pdf_writer.close()
            pdf_document.close()

        except Exception as e:
            print(f'Error merging PDF horizontally: {e}')

    def merge_two_pages_vertically(self, output_pdf, page_count):
        pdf_writer = fitz.open()
        pdf_document = fitz.open(self.input_pdf)
        num_pages = len(pdf_document)

        try:
            for i in range(0, num_pages, page_count):
                merged_page_width = max(self.pdf_document[j].rect.width for j in range(i, min(i + page_count, num_pages)))
                merged_page_height = sum(self.pdf_document[j].rect.height for j in range(i, min(i + page_count, num_pages)))

                merged_page = pdf_writer.new_page(width=merged_page_width, height=merged_page_height)
                y_offset = 0
                for j in range(i, min(i + page_count, num_pages)):
                    page = self.pdf_document[j]
                    draw_pdf_page(merged_page, page, 0, y_offset)
                    y_offset += page.rect.height

            pdf_writer.save(output_pdf)
            pdf_writer.close()
            pdf_document.close()

        except Exception as e:
            print(f'Error merging PDF vertically: {e}')


    def open_folder(self):
        if self.output_pdf:
            folder_path = os.path.dirname(self.output_pdf)
            os.startfile(folder_path)

    def get_output_filename(self):
        filename_dialog = QFileDialog()
        filename_dialog.setDefaultSuffix('pdf')
        filename_dialog.setAcceptMode(QFileDialog.AcceptSave)
        filename_dialog.setOption(QFileDialog.DontConfirmOverwrite, False)
        if filename_dialog.exec_():
            filenames = filename_dialog.selectedFiles()
            if filenames:
                return filenames[0]
        return None

    def update_page_indicator(self):
        self.page_indicator_label.setText(f'Page {self.current_page + 1} of {self.total_pages}')

def draw_pdf_page(merged_page, page, x_offset, y_offset):
    scale_factor = min(merged_page.rect.width / page.rect.width, merged_page.rect.height / page.rect.height)
    transform = fitz.Matrix(scale_factor, scale_factor).prerotate(0)
    page_pixmap = page.get_pixmap(matrix=transform)
    merged_page.insert_image(fitz.Rect(x_offset, y_offset, x_offset + page.rect.width * scale_factor, y_offset + page.rect.height * scale_factor), pixmap=page_pixmap)

class DropWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.parent = parent

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                file_path = str(url.toLocalFile())
                if file_path.lower().endswith('.pdf'):
                    self.parent.input_pdf = file_path  # Set input_pdf attribute in the main app
                    self.parent.load_pdf(file_path)
                    break

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PDFViewerApp()
    ex.show()
    sys.exit(app.exec_())
