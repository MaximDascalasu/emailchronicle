"""Offline investigation workspace and evidence inspector."""
import argparse
import csv
from datetime import date
import json
import hashlib
import os
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QDesktopServices, QColor, QAction, QKeySequence, QTextCursor
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QSplitter, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
    QFrame, QHeaderView, QTabWidget, QCheckBox, QMenu, QDialog, QDialogButtonBox, QPlainTextEdit)

from .reading import clean_message, readable_date, chronological, message_date, people_summary
from .parser import clean_address, parse_email
from .store import Store
from .search import search, plan, pattern, highlight_ranges, MAX_HIGHLIGHTS
from .qt_lifecycle import dispose_windows


class SourceViewer(QDialog):
    """Read-only, inert evidence display; never executes HTML or attachments."""
    def __init__(self, data, name, sha256, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle('Original email source · read only')
        self.resize(900, 650)
        layout = QVBoxLayout(self)
        identity = QLabel(f'{name}\nSHA-256: {sha256}\n{len(data):,} bytes · integrity checked before display')
        identity.setTextFormat(Qt.TextFormat.PlainText)
        identity.setWordWrap(True)
        identity.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(identity)
        tabs = QTabWidget()
        self.raw_text = QPlainTextEdit()
        self.raw_text.setReadOnly(True)
        is_msg = Path(name).suffix.lower() == '.msg'
        self.raw_text.setAccessibleName('Decoded MSG text, read only' if is_msg else 'Raw EML text, read only')
        self.raw_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        preview = data[:2*1024*1024].decode('utf-8', errors='replace')
        if is_msg:
            preview = '\n\n'.join(f'From: {m.sender or ""}\nTo: {m.recipients or ""}\nSubject: {m.subject or ""}\nDate: {m.raw_date or ""}\n\n{m.body}' for m in parse_email(data, '.msg'))
        self.raw_text.setPlainText(preview[:2*1024*1024])
        tabs.addTab(self.raw_text, 'Decoded MSG text' if is_msg else 'Raw EML text')
        self.hex_text = QPlainTextEdit()
        self.hex_text.setReadOnly(True)
        self.hex_text.setAccessibleName('Original byte hex preview')
        self.hex_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.hex_text.setPlainText('\n'.join(f'{offset:08x}  '+data[offset:offset+16].hex(' ')
            for offset in range(0, min(len(data), 65536), 16)))
        tabs.addTab(self.hex_text, 'Original bytes · hex')
        layout.addWidget(tabs)
        note = QLabel('MSG text is decoded message content; EML text is a UTF-8 preview. Hex shows exact original bytes.\n'
            'Display limits: first 2 MiB of text and first 64 KiB of hex. The preserved file stays complete.\n'
            'HTML, links and attachments are not executed. No external mail application is needed.')
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)



STYLE = """
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #24334b; }
QMainWindow, QWidget { background: #f3f5f9; }
QFrame#sidebar, QFrame#sidebar QLabel { background: #101a2c; color: #c6d3e8; }
QLabel#brand { color: white; font-size: 17px; font-weight: 700; }
QLabel#eyebrow { color: #8fa5c4; font-size: 10px; letter-spacing: 2px; }
QLabel#sidebarNote { color: #aebed4; font-size: 12px; line-height: 1.5; }
QLabel#navSelected { background: #263e60; color: white; border-radius: 7px; padding: 14px 6px; }
QLabel#pageTitle { font-size: 22px; font-weight: 700; color: #172942; }
QLabel#muted { color: #61718a; font-size: 11px; }
QLabel#metric { font-size: 25px; font-weight: 700; color: #1a3558; }
QLabel#sectionTitle { font-size: 12px; font-weight: 700; color: #61718a; }
QLabel#messageTitle { font-size: 17px; font-weight: 600; }
QFrame#card { background: white; border: 1px solid #dce3ee; border-radius: 9px; }
QFrame#card QLabel { background: transparent; }
QPushButton { background: white; border: 1px solid #cbd6e5; border-radius: 6px; padding: 7px 10px; font-weight: 600; }
QPushButton:hover { background: #e9f0fa; border-color: #829ec4; }
QPushButton:pressed { background: #dce8f9; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus { border: 2px solid #2868ce; }
QPushButton#primary { background: #225ec4; color: white; border-color: #225ec4; }
QPushButton#primary:hover { background: #184b9e; }
QPushButton:disabled { color: #8995a8; background: #e9edf3; border-color: #dce3ee; }
QLineEdit, QComboBox { background: white; border: 1px solid #cbd6e5; border-radius: 6px; padding: 7px; selection-background-color: #225ec4; }
QComboBox QAbstractItemView { background: white; color: #24334b; selection-background-color: #dce9ff; }
QTableWidget { background: white; alternate-background-color: #f8fafd; border: 1px solid #dce3ee; border-radius: 8px; selection-background-color: #dfebff; selection-color: #123d7c; }
QTableWidget::item { padding: 6px; border-bottom: 1px solid #edf1f6; }
QHeaderView::section { background: #eaf0f7; color: #54667f; font-size: 10px; font-weight: 700; border: 0; border-right: 2px solid #a9b9cf; padding: 10px 8px; }
QTextEdit { background: white; border: 0; padding: 10px; selection-background-color: #dce9ff; }
QTabWidget::pane { border: 1px solid #e0e6ee; background: white; }
QTabBar::tab { background: #f2f5fa; padding: 11px 10px; color: #61718a; }
QTabBar::tab:selected { background: white; color: #225ec4; border-bottom: 2px solid #225ec4; }
QSplitter::handle { background: #e3e9f2; width: 7px; }
QStatusBar { background: #e9eef6; color: #61718a; padding: 4px; }
QLabel#empty { color: #61718a; border: 1px dashed #b8c7da; border-radius: 8px; padding: 20px; }
QFrame#workflow { background: #eaf1fc; border: 1px solid #c8d9f2; border-radius: 8px; }
QLabel#guidance { background: transparent; color: #29486f; padding: 4px; }
QPushButton[workflowActive="true"] { background: #225ec4; color: white; border-color: #225ec4; }
QMenuBar, QMenu { background: white; }
QMenu::item:selected { background: #dfebff; }
QCheckBox { spacing: 8px; }
QLabel#timeCard { background: #f5f8ff; border: 1px solid #dce6f6; border-radius: 6px; padding: 12px; font-family: 'Consolas'; font-size: 11px; color: #395273; }
"""

class Window(QMainWindow):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.rows = []
        self.setWindowTitle("EmailChronicle — local evidence workspace")
        self.resize(1440, 900)
        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction("How to use EmailChronicle", self.show_help)
        help_menu.addAction("Third-party licenses", self.open_licenses)
        self.setMinimumSize(1040, 680)
        self.setStyleSheet(STYLE)
        root = QWidget()
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        self.setCentralWidget(root)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(185)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(16, 24, 16, 20)
        nav.setSpacing(16)
        brand = QLabel("EmailChronicle")
        brand.setObjectName("brand")
        nav.addWidget(brand)
        subtitle = QLabel("EVIDENCE WORKSPACE")
        subtitle.setObjectName("eyebrow")
        nav.addWidget(subtitle)
        nav.addSpacing(24)
        nav.addWidget(QLabel("INVESTIGATION"))
        self.cases = QComboBox()
        self.cases.setAccessibleName("Investigation")
        nav.addWidget(self.cases)
        new = QPushButton("+  New investigation")
        new.clicked.connect(self.new_case)
        nav.addWidget(new)
        nav.addSpacing(24)
        current = QLabel("  Chronological timeline")
        current.setObjectName("navSelected")
        nav.addWidget(current)
        explanation = QLabel("Every message linked to its evidence.\nEvery uncertainty kept visible.")
        explanation.setWordWrap(True)
        explanation.setObjectName("sidebarNote")
        nav.addWidget(explanation)
        nav.addStretch()
        local = QLabel("●  LOCAL WORKSPACE\nNo cloud processing\nEML / MSG evidence · CSV export")
        local.setObjectName("sidebarNote")
        nav.addWidget(local)
        shell.addWidget(sidebar)
        main = QWidget()
        layout = QVBoxLayout(main)
        layout.setContentsMargins(14, 10, 14, 8)
        layout.setSpacing(6)
        shell.addWidget(main, 1)
        top = QHBoxLayout()
        heading = QVBoxLayout()
        self.case_title = QLabel("Investigation timeline")
        self.case_title.setObjectName("pageTitle")
        heading.addWidget(self.case_title)
        caption = QLabel("Reconstruct the conversation. Trace every source.")
        caption.setObjectName("muted")
        heading.addWidget(caption)
        top.addLayout(heading, 1)
        self.export_button = QPushButton("Export ▾")
        export_menu = QMenu(self.export_button)
        export_menu.addAction("CSV · current visible messages", self.export_csv)
        export_menu.addAction("Report bundle · PDF, Excel & graphs", self.export_reports)
        self.export_button.setMenu(export_menu)
        self.export_button.setToolTip("Export visible messages to CSV or a complete report bundle")
        top.addWidget(self.export_button)
        self.import_button = QPushButton("+  Import evidence")
        self.import_button.setObjectName("primary")
        self.import_button.setToolTip("Import local EML or MSG files (Ctrl+O)")
        self.import_button.clicked.connect(self.import_files)
        top.addWidget(self.import_button)
        layout.addLayout(top)
        workflow = QFrame()
        workflow.setObjectName("workflow")
        journey = QVBoxLayout(workflow)
        journey.setContentsMargins(14, 12, 14, 12)
        journey.setSpacing(8)
        steps = QHBoxLayout()
        self.workflow_buttons = []
        for index, label in enumerate(("1  Create case", "2  Import EML / MSG", "3  Read timeline", "4  Check sources", "5  Export")):
            button = QPushButton(label)
            button.setAccessibleName("Workflow step " + label)
            button.clicked.connect(lambda checked=False, step=index: self.workflow_step(step))
            self.workflow_buttons.append(button)
            steps.addWidget(button, 1)
            if index < 4:
                arrow = QLabel("→")
                arrow.setStyleSheet("background: transparent; color: #61718a;")
                steps.addWidget(arrow)
        journey.addLayout(steps)
        self.guidance = QLabel()
        self.guidance.setObjectName("guidance")
        self.guidance.setWordWrap(True)
        journey.addWidget(self.guidance)
        self.overview_toggle = QPushButton("Show guidance & statistics ▾")
        self.overview_toggle.setCheckable(True)
        layout.addWidget(self.overview_toggle)
        layout.addWidget(workflow)
        workflow.hide()
        summary = QHBoxLayout()
        self.metrics = []
        self.metric_notes = []
        for label in ("CHRONOLOGICAL EVENTS", "NEEDS INVESTIGATOR REVIEW", "MESSAGES WITH DUPLICATE HINTS"):
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 10, 14, 10)
            card_layout.setSpacing(5)
            value = QLabel("0")
            value.setObjectName("metric")
            card_layout.addWidget(value)
            name = QLabel(label)
            name.setObjectName("muted")
            card_layout.addWidget(name)
            note = QLabel()
            note.setObjectName("muted")
            note.setWordWrap(True)
            card_layout.addWidget(note)
            self.metric_notes.append(note)
            self.metrics.append(value)
            summary.addWidget(card)
        summary_panel = QWidget()
        summary_panel.setLayout(summary)
        layout.addWidget(summary_panel)
        summary_panel.hide()
        self.overview_toggle.toggled.connect(workflow.setVisible)
        self.overview_toggle.toggled.connect(summary_panel.setVisible)
        filters = QHBoxLayout()
        self.keyword = QLineEdit()
        self.keyword.setPlaceholderText("Search subject or message content…")
        self.sender = QLineEdit()
        self.sender.setPlaceholderText("Sender")
        self.date_from = QLineEdit()
        self.date_from.setPlaceholderText("From YYYY-MM-DD")
        self.date_to = QLineEdit()
        self.date_to.setPlaceholderText("To YYYY-MM-DD")
        for widget, name in ((self.keyword, "Keyword filter"), (self.sender, "Sender filter"),
                              (self.date_from, "Recorded start date"), (self.date_to, "Recorded end date")):
            widget.setAccessibleName(name)
            widget.setClearButtonEnabled(True)
            filters.addWidget(widget, 2 if widget is self.keyword else 1)
            widget.textChanged.connect(self.refresh)
        self.density = QComboBox()
        self.density.addItems(["Compact", "Comfortable"])
        self.density.setAccessibleName("Timeline row density")
        self.density.currentIndexChanged.connect(self.change_density)
        filters.addWidget(self.density)
        clear = QPushButton("Reset")
        clear.clicked.connect(self.clear_filters)
        filters.addWidget(clear)
        layout.addLayout(filters)
        search_tools = QHBoxLayout()
        self.search_mode = QComboBox()
        self.search_mode.addItem("Exact terms / phrases", "exact")
        self.search_mode.addItem("Expanded · selected synonyms", "expanded")
        self.search_mode.addItem("Approximate · spelling tolerance", "approximate")
        self.search_mode.setAccessibleName("Search matching mode")
        self.search_mode.currentIndexChanged.connect(self.refresh)
        search_tools.addWidget(self.search_mode)
        dictionary_button = QPushButton("Synonyms & aliases…")
        dictionary_button.clicked.connect(self.edit_dictionary)
        search_tools.addWidget(dictionary_button)
        self.relevance = QCheckBox("Rank by relevance")
        self.relevance.toggled.connect(self.refresh)
        search_tools.addWidget(self.relevance)
        search_tools.addStretch()
        advanced_panel = QWidget()
        advanced_layout = QVBoxLayout(advanced_panel)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.addLayout(search_tools)
        self.search_info = QLabel("All terms required. Use quotes for phrases. No AI or external requests.")
        self.search_info.setTextFormat(Qt.TextFormat.PlainText)
        self.search_info.setObjectName("muted")
        self.search_info.setWordWrap(True)
        advanced_layout.addWidget(self.search_info)
        layout.addWidget(advanced_panel)
        advanced_panel.hide()
        advanced_button = QPushButton("Search options")
        advanced_button.setCheckable(True)
        advanced_button.toggled.connect(advanced_panel.setVisible)
        filters.addWidget(advanced_button)
        tools = QHBoxLayout()
        order = QLabel("TIMELINE   /   Oldest → newest · recorded send times  |  Drag column dividers ↔ to resize")
        self.order_label = order
        order.setObjectName("muted")
        tools.addWidget(order, 1)
        self.review_only = QCheckBox("Needs review only")
        self.review_only.toggled.connect(self.refresh)
        tools.addWidget(self.review_only)
        layout.addLayout(tools)
        self.empty = QLabel("Create an investigation to begin\nImport EML / MSG evidence to reconstruct a conversation.")
        self.empty.setObjectName("empty")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["DATE & TIME", "SENDER", "SUBJECT", "ORIGIN", "REVIEW"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(58)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setMinimumSectionSize(70)
        self.table.horizontalHeader().setToolTip("Drag the divider between headings to resize. Double-click a divider to fit the content.")
        for index, width in enumerate((185, 185, 230, 85, 160)):
            self.table.setColumnWidth(index, width)
        self.table.itemSelectionChanged.connect(self.show_message)
        splitter.addWidget(self.table)
        inspector = QFrame()
        inspector.setObjectName("card")
        inspector.setMinimumWidth(300)
        inspect_layout = QVBoxLayout(inspector)
        inspect_layout.setContentsMargins(10, 10, 10, 10)
        title = QLabel("Evidence inspector")
        title.setObjectName("sectionTitle")
        title.setMaximumHeight(18)
        inspect_layout.addWidget(title)
        self.message_title = QLabel("Select a message")
        self.message_title.setWordWrap(True)
        self.message_title.setMaximumHeight(48)
        self.message_title.setTextFormat(Qt.TextFormat.PlainText)
        self.message_title.setObjectName("messageTitle")
        inspect_layout.addWidget(self.message_title)
        self.match_info = QLabel()
        self.match_info.setTextFormat(Qt.TextFormat.PlainText)
        self.match_info.setWordWrap(True)
        self.match_info.hide()
        self.match_info.setObjectName("muted")
        inspect_layout.addWidget(self.match_info)
        self.tabs = QTabWidget()
        self.body_view = QTextEdit()
        self.body_view.setReadOnly(True)
        self.body_view.setAccessibleName("Cleaned message content")
        self.body_view.setPlaceholderText("Select a timeline row to read the message.")
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setAccessibleName("Message content and provenance")
        message_panel = QWidget()
        message_layout = QVBoxLayout(message_panel)
        message_layout.setContentsMargins(10, 10, 10, 10)
        message_layout.setSpacing(10)
        self.time_card = QLabel("Select a message to inspect its date metadata.")
        self.time_card.setTextFormat(Qt.TextFormat.PlainText)
        self.time_card.setWordWrap(True)
        self.time_card.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.time_card.setObjectName("timeCard")
        self.time_card.setAccessibleName("Date and time breakdown")
        self.time_card.hide()
        self.message_meta = QLabel()
        self.message_meta.setTextFormat(Qt.TextFormat.PlainText)
        self.message_meta.setWordWrap(True)
        self.message_meta.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        message_layout.addWidget(self.message_meta)
        self.body_view.setMinimumHeight(180)
        self.body_view.setStyleSheet("QTextEdit { font-size: 14px; padding: 12px; background: white; }")
        message_layout.addWidget(self.body_view, 1)
        self.tabs.addTab(message_panel, "Message")
        self.tabs.addTab(self.detail, "Source details")
        self.original_text = QPlainTextEdit()
        self.original_text.setReadOnly(True)
        self.tabs.addTab(self.original_text, "Original text")
        inspect_layout.addWidget(self.tabs, 1)
        self.source_button = QPushButton("Open verified source copy")
        self.source_button.clicked.connect(self.open_source)
        self.source_button.setEnabled(False)
        inspect_layout.addWidget(self.source_button)
        note = QLabel("Original evidence preserved · Details in Source details.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        inspect_layout.addWidget(note)
        splitter.addWidget(inspector)
        splitter.setSizes([650, 520])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        self.reader_splitter = splitter
        layout.addWidget(splitter, 1)
        self.statusBar().setSizeGripEnabled(False)
        for shortcut, callback in (("Ctrl+O", self.import_files), ("Ctrl+N", self.new_case),
                                   ("Ctrl+E", self.export_csv), ("Ctrl+F", self.keyword.setFocus)):
            action = QAction(self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(callback)
            self.addAction(action)
        self.cases.currentIndexChanged.connect(self.refresh)
        self.reload_cases()

    def change_density(self):
        self.table.verticalHeader().setDefaultSectionSize(58 if self.density.currentIndex() == 0 else 82)

    def clear_filters(self):
        for field in (self.sender, self.keyword, self.date_from, self.date_to):
            field.blockSignals(True)
            field.clear()
            field.blockSignals(False)
        self.review_only.blockSignals(True)
        self.review_only.setChecked(False)
        self.review_only.blockSignals(False)
        self.search_mode.blockSignals(True)
        self.search_mode.setCurrentIndex(0)
        self.search_mode.blockSignals(False)
        self.relevance.blockSignals(True)
        self.relevance.setChecked(False)
        self.relevance.blockSignals(False)
        self.refresh()

    def search_settings(self):
        return {"query": self.keyword.text(), "mode": self.search_mode.currentData(),
                "rank_by_relevance": self.relevance.isChecked(),
                "dictionary": self.store.search_dictionary(self.cases.currentData()),
                "semantics": "AND between terms; quoted phrases; whole-word case-insensitive matches; approximate cutoff 0.84 for alphabetic terms of 5+ characters"}

    def edit_dictionary(self):
        case = self.cases.currentData()
        if case is None:
            QMessageBox.information(self, "Investigation required", "Create an investigation first.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Investigation synonyms & aliases")
        dialog.resize(680, 440)
        layout = QVBoxLayout(dialog)
        label = QLabel("One group per line: + Group name | term | synonym | alias\n"
            "Use + to enable a group, - to exclude it. No groups are enabled by default.\n"
            "Example: + Payment | payment | remittance\n"
            "Only complete query terms or quoted phrases expand. Context matters: review ambiguous synonyms.\n"
            "Changes apply only to this investigation and are versioned in its audit trail.")
        label.setWordWrap(True)
        layout.addWidget(label)
        editor = QTextEdit()
        editor.setAcceptRichText(False)
        editor.setAccessibleName("Synonym groups and selected expansions")
        groups = self.store.search_dictionary(case)['groups']
        editor.setPlainText('\n'.join(('+' if g['enabled'] else '-')+' '+g['name']+' | '+' | '.join(g['terms']) for g in groups))
        layout.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(dialog.reject)
        def save():
            try:
                result = []
                for line in editor.toPlainText().splitlines():
                    if not line.strip():
                        continue
                    parts = [p.strip() for p in line.strip()[1:].split('|')]
                    if line.strip()[0] not in '+-' or len(parts) < 3:
                        raise ValueError('Use + or -, a group name, and at least two terms separated by |.')
                    result.append({'name': parts[0], 'terms': parts[1:], 'enabled': line.strip().startswith('+')})
                self.store.save_search_dictionary(case, result)
            except ValueError as exc:
                QMessageBox.warning(dialog, "Check synonym groups", str(exc))
            else:
                dialog.accept()
        buttons.accepted.connect(save)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def set_guidance(self, step, text):
        self.guidance.setText(text)
        for index, button in enumerate(self.workflow_buttons):
            button.setProperty("workflowActive", index == step)
            button.style().unpolish(button)
            button.style().polish(button)

    def workflow_step(self, step):
        if step == 0:
            self.new_case()
        elif self.cases.currentData() is None:
            self.set_guidance(0, "Start here: create an investigation. It keeps this case's evidence separate from other cases.")
        elif step == 1:
            self.import_files()
        elif step == 2:
            self.set_guidance(2, "Read oldest → newest by recorded send time. Missing timezones are labeled; unknown dates stay last. Select a row to read its message; use search to narrow the timeline.")
            self.table.setFocus()
        elif step == 3:
            self.tabs.setCurrentIndex(1)
            self.set_guidance(3, "Check Provenance & review for raw dates, quoted headers, duplicate hints and SHA-256. Open verified source copy checks file integrity; it does not verify the email author's identity.")
            self.detail.setFocus()
        elif step == 4:
            self.set_guidance(4, "Export saves only the messages visible under your current filters. Include undated and flagged messages where relevant; CSV keeps provenance and review flags.")
            if self.rows:
                self.export_button.showMenu()

    def show_help(self):
        QMessageBox.information(self, "How EmailChronicle works",
            "1. Create an investigation, then import EML or MSG files.\n"
            "2. The app preserves a hashed copy of each file and extracts messages.\n"
            "3. Recorded dates are sorted oldest first. Offsets are normalized to UTC; missing timezones are labeled.\n"
            "4. Review quoted headers, missing dates and likely duplicates manually.\n"
            "5. Select a message to inspect its content and source. Export visible rows to CSV or a PDF/Excel/graph bundle.\n\n"
            "Original files are never modified by the importer. All evidence stays in your local workspace.\n"
            "Quoted headers are unverified text. No missing times or senders are invented.\n\n"
            f"Workspace: {self.store.directory}")

    def open_licenses(self):
        if getattr(sys, "frozen", False):
            path = Path(sys._MEIPASS) / "third-party-notices"
        else:
            root = Path(__file__).resolve().parents[2]
            path = root / "build" / "compliance" / "third-party-notices"
            if not path.is_dir():
                path = root / "THIRD_PARTY_NOTICES.md"
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.warning(self, "Third-party licenses", f"Could not open {path}")

    def reload_cases(self, selected=None):
        self.cases.blockSignals(True)
        self.cases.clear()
        for row in self.store.investigations():
            self.cases.addItem(row["name"], row["id"])
        if selected is not None:
            self.cases.setCurrentIndex(self.cases.findData(selected))
        self.cases.blockSignals(False)
        self.refresh()

    def new_case(self):
        name, ok = QInputDialog.getText(self, "New investigation", "Investigation name:")
        if ok and name.strip():
            self.reload_cases(self.store.create_investigation(name))

    def import_files(self):
        case = self.cases.currentData()
        if case is None:
            QMessageBox.information(self, "Investigation required", "Create an investigation first.")
            return
        paths, _ = QFileDialog.getOpenFileNames(self, "Import evidence", "", "Email files (*.eml *.msg)")
        count, skipped, failures = 0, 0, []
        for path in paths:
            try:
                added = self.store.import_email(case, path)
                count += added
                skipped += added == 0
            except Exception as exc:
                failures.append(f"{Path(path).name}: {exc}")
                with self.store.db:
                    self.store.audit(case, "import_failed", {"path": path, "error": str(exc)})
        self.refresh()
        if paths:
            QMessageBox.information(self, "Import result", f"Extracted {count} messages. Skipped {skipped} exact duplicate files.\n" + "\n".join(failures))

    def refresh(self):
        case = self.cases.currentData()
        case_rows = self.store.timeline(case) if case is not None else []
        has_evidence = bool(case_rows)
        self.workflow_buttons[1].setEnabled(case is not None)
        for button in self.workflow_buttons[2:]:
            button.setEnabled(has_evidence)
        if case is None:
            self.set_guidance(0, "Start here: create an investigation. It keeps this case's evidence separate from other cases.")
        elif not has_evidence:
            self.set_guidance(1, "Next: import EML or MSG files in any order. The app preserves copies and hashes, extracts messages, and sorts recorded send times, retaining missing-timezone notices.")
        else:
            self.set_guidance(2, "Next: read the timeline, then check sources and review flags before exporting. Highlighted steps are guidance, not a record that evidence has been reviewed.")
        previous = self.selected()
        selected_id = previous["id"] if previous else None
        self.case_title.setText(self.cases.currentText() or "Investigation timeline")
        self.import_button.setEnabled(self.cases.currentData() is not None)
        self.source_button.setEnabled(False)
        self.body_view.clear()
        self.match_info.clear()
        self.time_card.setText("Select a message to inspect its date metadata.")
        self.message_title.setText("Select a message")
        try:
            start, end = self.date_from.text().strip(), self.date_to.text().strip()
            for value in (start, end):
                if value and date.fromisoformat(value).isoformat() != value:
                    raise ValueError("Use YYYY-MM-DD")
            if start and end and start > end:
                raise ValueError("Start date must not follow end date")
        except ValueError:
            self.rows = []
            self.table.setRowCount(0)
            self.detail.clear()
            for metric in self.metrics:
                metric.setText("—")
            self.export_button.setEnabled(False)
            self.empty.setText("Check the date filters · use YYYY-MM-DD")
            self.empty.show()
            self.statusBar().showMessage("Invalid date range. Use YYYY-MM-DD, with start before end.")
            return
        candidates = self.store.timeline(self.cases.currentData(), self.sender.text(), "",
                                        self.date_from.text().strip(), self.date_to.text().strip())
        settings = self.search_settings()
        try:
            query_plan = plan(settings['query'], settings['mode'], settings['dictionary']['groups'])
            self.rows = search(candidates, settings['query'], settings['mode'], settings['dictionary']['groups'], settings['rank_by_relevance'])
        except ValueError as exc:
            self.rows = []
            self.search_info.setText(str(exc))
        else:
            expansions = [f"{term} → " + ', '.join(actual for actual, reason, group in alternatives if reason != 'exact')
                          for term, alternatives in query_plan if len(alternatives) > 1]
            self.search_info.setText("All terms required · quote phrases · dictionary v" + str(settings['dictionary']['version']) +
                (" · Selected expansions: " + '; '.join(expansions) if expansions else " · No synonym expansions selected for this query") +
                (" · Approximate matches are spelling suggestions, not equivalent meanings." if settings['mode'] == 'approximate' else ""))
        self.order_label.setText("RESULTS   /   Relevance · chronology breaks ties" if self.relevance.isChecked() and self.keyword.text().strip()
                                else "TIMELINE / Oldest → newest · recorded send times · * timezone not recorded | Drag heading dividers ↔ to resize")
        if self.review_only.isChecked():
            self.rows = [row for row in self.rows if json.loads(row["flags"]) or row["duplicate_count"]]
        self.metrics[0].setText(str(len(self.rows)))
        self.metrics[1].setText(str(sum(bool(json.loads(r["flags"])) or bool(r["duplicate_count"]) for r in self.rows)))
        self.metrics[2].setText(str(sum(bool(r["duplicate_count"]) for r in self.rows)))
        self.metric_notes[0].setText(f"{len(self.rows)} visible / {len(case_rows)} in investigation")
        self.metric_notes[1].setText("Dates, quoted headers and duplicate hints")
        self.metric_notes[2].setText("Review hints · occurrences remain separate")
        self.export_button.setEnabled(bool(self.rows))
        self.empty.setVisible(not self.rows)
        self.empty.setText("No messages match these filters. Try Reset." if self.cases.currentData() is not None else
                           "Create an investigation to begin\nThen import local EML or MSG evidence.")
        self.table.setRowCount(0)
        self.detail.clear()
        for i, row in enumerate(self.rows):
            self.table.insertRow(i)
            flags = json.loads(row["flags"])
            if row["duplicate_count"]:
                flags.append("likely_duplicate")
            display_date = message_date(row).replace(" · timezone not recorded", " (local*)").replace(" · ", "\n", 1)
            for col, value in enumerate((display_date, (row["sender"] or "Unknown") + "\nTo: " + (row["recipients"] or "[missing]"),
                                         row["subject"] or "(no subject)", row["kind"].capitalize(),
                                         ", ".join(flag.replace("_", " ").capitalize() for flag in flags))):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if col == 4 and flags:
                    item.setForeground(QColor("#946200"))
                self.table.setItem(i, col, item)
        if self.rows:
            target = next((i for i, r in enumerate(self.rows) if r["id"] == selected_id), 0)
            self.table.selectRow(target)
        self.statusBar().showMessage(f"{len(self.rows)} messages · Local workspace: {self.store.directory}")

    def selected(self):
        index = self.table.currentRow()
        return self.rows[index] if 0 <= index < len(self.rows) else None

    def show_message(self):
        row = self.selected()
        if row:
            self.source_button.setEnabled(True)
            self.time_card.setText(
                "DATE & TIME BREAKDOWN\n\n"
                f"NORMALIZED UTC   {row['date_utc'] or '[unknown — review required]'}\n"
                f"RAW DATE   {row['raw_date'] or '[missing date header]'}\n"
                f"ORIGIN   {row['kind']} · {row['locator']}\n"
                "Known offsets are normalized to UTC. Unknown dates are never guessed.")
            self.message_title.setText(row["subject"] or "(no subject)")
            self.message_meta.setText(f"Sent: {message_date(row)}\nFrom: {people_summary(row['sender']) or '[missing]'}\nTo: {people_summary(row['recipients']) or '[not recorded in quoted header]'}")
            self.message_meta.setToolTip(f"From: {clean_address(row['sender'])}\nTo: {clean_address(row['recipients'])}")
            self.body_view.setPlainText(clean_message(row['body'], row['sender']) or '[No message text after cleaning; see Provenance & review.]')
            self.tabs.setCurrentIndex(0)
            self.body_view.moveCursor(QTextCursor.MoveOperation.Start)
            self.original_text.setPlainText(row['body'])
            matches = row.get('search_matches', [])
            explanations = list(dict.fromkeys(f"{m['query']} → {m['matched']} ({m['reason']}, {m['field']}" +
                (f", group: {m['group']}" if m['group'] else "") + ")" for m in matches))
            self.match_info.setText("Matched: " + '; '.join(explanations[:8]) if explanations else "")
            self.match_info.setVisible(bool(self.match_info.text()))
            selections = []
            content = self.body_view.toPlainText()
            spans = highlight_ranges(content, (m['matched'] for m in matches))
            for start, end in spans:
                selection = QTextEdit.ExtraSelection()
                cursor = self.body_view.textCursor()
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
                selection.cursor = cursor
                selection.format.setBackground(QColor('#fff0a8'))
                selections.append(selection)
            if row.get('search_matches_limited') or len(spans) >= MAX_HIGHLIGHTS:
                self.match_info.setText(self.match_info.text() + '\nDisplay highlights/explanations are limited; complete evidence is preserved.')
            self.body_view.setExtraSelections(selections)
            self.detail.setPlainText(
                f"From: {row['sender'] or '[missing]'}\nTo: {row['recipients'] or '[missing]'}\n"
                f"Subject: {row['subject'] or '[missing]'}\nOriginal date text: {row['raw_date'] or '[missing]'}\n"
                f"Origin: {row['kind']}\nLocation: {row['locator']}\n"
                f"Review flags: {row['flags']}\nLikely duplicates: {row['duplicate_count']}\n"
                f"Submitted source: {row['original_path']}\nPreserved copy: {row['stored_path']}\n"
                f"SHA-256: {row['sha256']}\n\nComplete extracted text is available in the Original text tab.")

    def open_source(self, checked=False, *, external=False):
        row = self.selected()
        if row:
            try:
                path = self.store.verified_source(row["id"])
                if external:
                    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
                        raise OSError('No external email viewer is configured. Use the built-in source viewer instead.')
                else:
                    data = path.read_bytes()
                    if hashlib.sha256(data).hexdigest() != row['sha256']:
                        raise ValueError('Evidence copy changed while opening; display blocked.')
                    self.source_dialog = SourceViewer(data, Path(row['original_path']).name, row['sha256'], self)
                    self.source_dialog.show()
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "Open source", str(exc))

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export visible timeline", "timeline.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            # Block overwriting originals, managed evidence, or application storage.
            target = Path(path).resolve()
            sources = self.store.db.execute("SELECT original_path, stored_path FROM sources").fetchall()
            protected = {Path(r[k]).resolve() for r in sources for k in ("original_path", "stored_path")}
            if target in protected or target.is_relative_to(self.store.directory):
                raise ValueError("Choose an export location outside the workspace and original evidence files.")
            with target.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["Sent date & time", "Sender", "Receiver", "Subject", "Message"])
                for row in chronological(self.rows):
                    writer.writerow([safe_cell(value) for value in (
                        message_date(row), clean_address(row['sender']), clean_address(row['recipients']),
                        row['subject'], clean_message(row['body'], row['sender']))])
            with self.store.db:
                self.store.audit(self.cases.currentData(), "export_csv", {"path": str(target), "messages": len(self.rows), "search": self.search_settings()})
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Export failed", str(exc))

    def export_reports(self):
        if self.cases.currentData() is None or not self.rows:
            QMessageBox.information(self, "Nothing to export", "Select an investigation with visible messages first.")
            return
        answer = QMessageBox.question(self, "Export visible timeline",
            f"Export {len(self.rows)} visible message occurrences with the current filters?\n\n"
            "Creates a PDF report, Excel workbook, timeline, Gantt-style event lanes and communication graphs "
            "in PNG and SVG. Includes complete message content and source paths.\n\n"
            "Duplicate occurrences remain included. Undated messages stay off the time axis. "
            "The audit worksheet covers the whole investigation. No manual review completion is inferred.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        parent = QFileDialog.getExistingDirectory(self, "Choose report destination outside the evidence workspace")
        if not parent:
            return
        from .exports import export_bundle
        filters = {"sender": self.sender.text(), "keywords": self.keyword.text(),
                   "utc_from": self.date_from.text(), "utc_to": self.date_to.text(),
                   "needs_review_only": self.review_only.isChecked()}
        filters['search'] = self.search_settings()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            folder = export_bundle(self.store, self.cases.currentData(), self.rows, parent, filters)
        except Exception as exc:
            QMessageBox.warning(self, "Report export failed", str(exc))
        else:
            QMessageBox.information(self, "Report bundle ready", f"Saved reports and graphs to:\n{folder}\n\n"
                "Review the scope and warnings before sharing. SHA256SUMS.json records output hashes.")
        finally:
            QApplication.restoreOverrideCursor()


def safe_cell(value):
    text = "" if value is None else str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")) else text


def main():
    parser = argparse.ArgumentParser(description="Offline email evidence timeline")
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("LOCALAPPDATA", Path.home())) / "EmailChronicle")
    parser.add_argument("--test-close-after-ms", type=int, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.test_close_after_ms is not None and not 100 <= args.test_close_after_ms <= 60000:
        parser.error('Test close delay must be between 100 and 60000 milliseconds')
    app = QApplication(sys.argv[:1])
    store = Store(args.data_dir)
    window = Window(store)
    window.show()
    if args.test_close_after_ms is not None:
        QTimer.singleShot(args.test_close_after_ms, window.close)
    try:
        return app.exec()
    finally:
        dispose_windows()
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
