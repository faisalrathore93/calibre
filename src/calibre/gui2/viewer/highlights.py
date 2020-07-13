#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPL v3 Copyright: 2020, Kovid Goyal <kovid at kovidgoyal.net>

from itertools import chain

from PyQt5.Qt import (
    QHBoxLayout, QIcon, QItemSelectionModel, QKeySequence, QLabel, QListWidget,
    QListWidgetItem, QPushButton, Qt, QTextEdit, QToolButton, QVBoxLayout, QWidget,
    pyqtSignal
)

from calibre.constants import plugins
from calibre.gui2 import error_dialog, question_dialog
from calibre.gui2.library.annotations import Details
from calibre.gui2.viewer.search import SearchInput
from calibre.gui2.viewer.shortcuts import index_to_key_sequence
from calibre.gui2.widgets2 import Dialog
from polyglot.builtins import range


class Highlights(QListWidget):

    jump_to_highlight = pyqtSignal(object)
    current_highlight_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        QListWidget.__init__(self, parent)
        self.setSpacing(2)
        pi = plugins['progress_indicator'][0]
        pi.set_no_activate_on_click(self)
        self.itemActivated.connect(self.item_activated)
        self.currentItemChanged.connect(self.current_item_changed)
        self.uuid_map = {}

    def current_item_changed(self, current, previous):
        self.current_highlight_changed.emit(current.data(Qt.UserRole) if current is not None else None)

    def load(self, highlights):
        self.clear()
        self.uuid_map = {}
        for h in highlights or ():
            txt = h.get('highlighted_text')
            if not h.get('removed') and txt:
                i = QListWidgetItem(txt, self)
                i.setData(Qt.UserRole, h)
                self.uuid_map[h['uuid']] = self.count() - 1

    def refresh(self, highlights):
        h = self.current_highlight
        self.load(highlights)
        if h is not None:
            idx = self.uuid_map.get(h['uuid'])
            if idx is not None:
                self.set_current_row(idx)

    def find_query(self, query):
        cr = self.currentRow()
        pat = query.regex
        if query.backwards:
            if cr < 0:
                cr = self.count()
            indices = chain(range(cr - 1, -1, -1), range(self.count() - 1, cr, -1))
        else:
            if cr < 0:
                cr = -1
            indices = chain(range(cr + 1, self.count()), range(0, cr + 1))
        for i in indices:
            item = self.item(i)
            h = item.data(Qt.UserRole)
            if pat.search(h['highlighted_text']) is not None or pat.search(h.get('notes') or '') is not None:
                self.set_current_row(i)
                return True
        return False

    def set_current_row(self, row):
        self.setCurrentRow(row, QItemSelectionModel.ClearAndSelect)

    def item_activated(self, item):
        self.jump_to_highlight.emit(item.data(Qt.UserRole))

    @property
    def current_highlight(self):
        i = self.currentItem()
        if i is not None:
            return i.data(Qt.UserRole)


class NotesEditDialog(Dialog):

    def __init__(self, notes, parent=None):
        self.initial_notes = notes
        Dialog.__init__(self, name='edit-notes-highlight', title=_('Edit notes'), parent=parent)

    def setup_ui(self):
        l = QVBoxLayout(self)
        self.qte = qte = QTextEdit(self)
        qte.setMinimumHeight(400)
        qte.setMinimumWidth(600)
        if self.initial_notes:
            qte.setPlainText(self.initial_notes)
        l.addWidget(qte)
        l.addWidget(self.bb)

    @property
    def notes(self):
        return self.qte.toPlainText().rstrip()


class NotesDisplay(QWidget):

    notes_edited = pyqtSignal(object)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.browser = nd = Details(self)
        h.addWidget(nd)
        self.edit_button = eb = QToolButton(self)
        eb.setIcon(QIcon(I('modified.png')))
        eb.setToolTip(_('Edit the notes for this highlight'))
        h.addWidget(eb)
        eb.clicked.connect(self.edit_notes)

    def show_notes(self, text=''):
        text = (text or '').strip()
        self.setVisible(bool(text))
        self.browser.setPlainText(text)
        h = self.browser.document().size().height() + 8
        self.browser.setMaximumHeight(h)
        self.setMaximumHeight(max(self.edit_button.sizeHint().height() + 4, h))

    def edit_notes(self):
        current_text = self.browser.toPlainText()
        d = NotesEditDialog(current_text, self)
        if d.exec_() == d.Accepted and d.notes != current_text:
            self.notes_edited.emit(d.notes)


class HighlightsPanel(QWidget):

    jump_to_cfi = pyqtSignal(object)
    request_highlight_action = pyqtSignal(object, object)
    web_action = pyqtSignal(object, object)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setFocusPolicy(Qt.NoFocus)
        self.l = l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        self.search_input = si = SearchInput(self, 'highlights-search')
        si.do_search.connect(self.search_requested)
        l.addWidget(si)

        la = QLabel(_('Double click to jump to an entry'))
        la.setWordWrap(True)
        l.addWidget(la)

        self.highlights = h = Highlights(self)
        l.addWidget(h)
        h.jump_to_highlight.connect(self.jump_to_highlight)
        h.current_highlight_changed.connect(self.current_highlight_changed)
        self.load = h.load
        self.refresh = h.refresh

        self.h = h = QHBoxLayout()
        l.addLayout(h)

        def button(icon, text, tt, target):
            b = QPushButton(QIcon(I(icon)), text, self)
            b.setToolTip(tt)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(target)
            return b

        self.add_button = button('plus.png', _('Add'), _('Create a new highlight'), self.add_highlight)
        self.edit_button = button('edit_input.png', _('Edit'), _('Edit the selected highlight'), self.edit_highlight)
        self.remove_button = button('trash.png', _('Remove'), _('Remove the selected highlight'), self.remove_highlight)
        h.addWidget(self.add_button), h.addWidget(self.edit_button), h.addWidget(self.remove_button)

        self.notes_display = nd = NotesDisplay(self)
        nd.notes_edited.connect(self.notes_edited)
        l.addWidget(nd)
        nd.setVisible(False)

    def notes_edited(self, text):
        h = self.highlights.current_highlight
        if h is not None:
            h['notes'] = text
            self.web_action.emit('set-notes-in-highlight', h)

    def set_tooltips(self, rmap):
        a = rmap.get('create_annotation')
        if a:

            def as_text(idx):
                return index_to_key_sequence(idx).toString(QKeySequence.NativeText)

            tt = self.add_button.toolTip().partition('[')[0].strip()
            keys = sorted(filter(None, map(as_text, a)))
            if keys:
                self.add_button.setToolTip('{} [{}]'.format(tt, ', '.join(keys)))

    def search_requested(self, query):
        if not self.highlights.find_query(query):
            error_dialog(self, _('No matches'), _(
                'No highlights match the search: {}').format(query.text), show=True)

    def focus(self):
        self.highlights.setFocus(Qt.OtherFocusReason)

    def jump_to_highlight(self, highlight):
        self.request_highlight_action.emit(highlight['uuid'], 'goto')

    def current_highlight_changed(self, highlight):
        nd = self.notes_display
        if highlight is None or not highlight.get('notes'):
            nd.show_notes()
        else:
            nd.show_notes(highlight['notes'])

    def no_selected_highlight(self):
        error_dialog(self, _('No selected highlight'), _(
            'No highlight is currently selected'), show=True)

    def edit_highlight(self):
        h = self.highlights.current_highlight
        if h is None:
            return self.no_selected_highlight()
        self.request_highlight_action.emit(h['uuid'], 'edit')

    def remove_highlight(self):
        h = self.highlights.current_highlight
        if h is None:
            return self.no_selected_highlight()
        if question_dialog(self, _('Are you sure?'), _(
            'Are you sure you want to delete this highlight permanently?')
        ):
            self.request_highlight_action.emit(h['uuid'], 'delete')

    def add_highlight(self):
        self.request_highlight_action.emit(None, 'create')
