
import os.path as op
import sys
from medinx import parse_folder, unformat_values, format_values

import logging
logger = logging.getLogger('medinx')

from PyQt5 import QtCore, QtGui, QtWidgets

class MdataTableEditorMain(QtWidgets.QWidget):
    """ 
    Display a QTableView with MdataTableModel.
    Use MdataTableCellDelegate to show previous text while editing
    """
    def __init__(self, folder_to_parse, *args):
        QtWidgets.QWidget.__init__(self, *args)

        self.tablemodel = MdataTableModel(parse_folder(folder_to_parse), self)
        tableview = QtWidgets.QTableView()
        tableview.setModel(self.tablemodel)
        delegate = MdataTableCellDelegate()
        tableview.setItemDelegate(delegate)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(tableview)
        self.setLayout(layout)

        self.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self.shortcut.activated.connect(self.tablemodel.on_save)

    def closeEvent(self, event):

        quit_msg = "Save?"
        reply = QtWidgets.QMessageBox.question(self, 'Message', quit_msg,
                                               QtWidgets.QMessageBox.Yes,
                                               QtWidgets.QMessageBox.No)
    
        if reply == QtWidgets.QMessageBox.Yes:
            self.tablemodel.on_save()
            
        event.accept()
            
class MdataTableCellDelegate(QtWidgets.QStyledItemDelegate):
    """ Show previous text while editing """
    
    def createEditor(self, parent, option, index):
        return super(MdataTableCellDelegate, self).createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        text = index.data(QtCore.Qt.EditRole) or index.data(QtCore.Qt.DisplayRole)
        editor.setText(text)         

        
class MdataTableModel(QtCore.QAbstractTableModel):
    def __init__(self, mdata_index, parent=None, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)

        self.attributes = mdata_index.get_attributes()
        self.attribute_types = mdata_index.get_attribute_types()
        self.file_names = mdata_index.get_files()
        self.mdata_index = mdata_index

    def flags(self, index):
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        
    def rowCount(self, parent=None):
        return len(self.file_names)

    def columnCount(self, parent=None):
        return len(self.attributes)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Vertical:
                return QtCore.QVariant(op.basename(self.file_names[section]))
            elif orientation == QtCore.Qt.Horizontal:
                return QtCore.QVariant(self.attributes[section])
        if role == QtCore.Qt.ToolTipRole:
            if orientation == QtCore.Qt.Vertical:
                return QtCore.QVariant(op.dirname(self.file_names[section]))

        return QtCore.QVariant()

    
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return QtCore.QVariant()
        elif role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        fn = self.file_names[index.row()]
        attr = self.attributes[index.column()]
        values = format_values(self.mdata_index.get_metadata(fn).get(attr, []))
        return QtCore.QVariant(values)

    
    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role == QtCore.Qt.EditRole:
            attr = self.attributes[index.column()]
            try:
                conv_vals = unformat_values(value, self.attribute_types[attr])
            except (ValueError, TypeError) as e:
                logger.error('Could not unformat %s while setting attr %s',
                             value, attr)
                return False
            self.mdata_index.set_metadata_attr(self.file_names[index.row()],
                                               attr, conv_vals)
            # self.dataChanged.emit(index, index)
            return True
        return False

    @QtCore.pyqtSlot()
    def on_save(self):
        self.mdata_index.save()
