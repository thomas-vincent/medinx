from PyQt5 import QtCore, QtGui, QtWidgets
import sys

from iso8601 import parse_date

def main():
    app = QtWidgets.QApplication(sys.argv)
    main_widget = MdataTableEditorMain()
    main_widget.show()
    sys.exit(app.exec_())

class MdataTableEditorMain(QtWidgets.QWidget):
    def __init__(self, *args):
        QtWidgets.QWidget.__init__(self, *args)

        tablemodel = MdataTableModel(self)
        tableview = QtWidgets.QTableView()
        tableview.setModel(tablemodel)
        delegate = MdataTableCellDelegate()
        tableview.setItemDelegate(delegate)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(tableview)
        self.setLayout(layout)

class MdataTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent=None, *args):
        def split(s):
            return [e.strip() for e in s.strip('[]').split(',')]

        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.attributes = ['counter', 'author', 'reviewed', 'cdate']
        self.formatters = [lambda vs: '['+', '.join(['%s'%v for v in vs])+']',
                           lambda vs: '['+', '.join(vs)+']',
                           lambda vs: '['+', '.join(['%s'%v for v in vs])+']',
                           lambda vs: '['+', '.join([v.isoformat('T') for v in vs])+']']
        self.unformatters = [lambda s: [int(v) for v in split(s)],
                             lambda s: split(s),
                             lambda s: [v.lower()=='true' for v in split(s)],
                             lambda s: [parse_date(v) for v in split(s)],
                             ]
        self._file_table = [('fn1', [[1,2,3], ['me','myself'], ['True'], []]),
                            ('fn2', [[], ['you'], [], [parse_date('2016')]]),
                            ('fn3', [[3], [], [], []])]

    def flags(self, index):
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        
    def rowCount(self, parent):
        return len(self._file_table)

    def columnCount(self, parent):
        return len(self.attributes)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Vertical:
                return QtCore.QVariant(self._file_table[section][0])
            elif orientation == QtCore.Qt.Horizontal:
                return QtCore.QVariant(self.attributes[section])
        return QtCore.QVariant()
    
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return QtCore.QVariant()
        elif role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()

        value = self._file_table[index.row()][1][index.column()]
        return QtCore.QVariant(self.formatters[index.column()](value))

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role == QtCore.Qt.EditRole:
            try:
                unformatted_value = self.unformatters[index.column()](value)
            except ValueError:
                return False
            self._file_table[index.row()][1][index.column()] = unformatted_value
            # self.dataChanged.emit(index, index)
            return True
        return False

class MdataTableCellDelegate(QtWidgets.QStyledItemDelegate):

    def createEditor(self, parent, option, index):
        return super(MdataTableCellDelegate, self).createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        text = index.data(QtCore.Qt.EditRole) or index.data(QtCore.Qt.DisplayRole)
        editor.setText(text)         



class EditButtonsWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(EditButtonsWidget,self).__init__(parent)

        # add your buttons
        layout = QtGui.QHBoxLayout()

        # adjust spacings to your needs
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        # add your buttons
        layout.addWidget(QtWidgets.QPushButton('Save'))
        layout.addWidget(QtWidgets.QPushButton('Edit'))
        layout.addWidget(QtWidgets.QPushButton('Delete'))

        self.setLayout(layout)
        
class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent)

        if parent is not None:
            self.setMargin(margin)

        self.setSpacing(spacing)

        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList[index]

        return None

    def takeAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList.pop(index)

        return None

    def expandingDirections(self):
        return QtCore.Qt.Orientations(QtCore.Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QtCore.QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()

        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())

        size += QtCore.QSize(2 * self.contentsMargins().top(),
                             2 * self.contentsMargins().top())
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            spaceX = self.spacing() + \
                     wid.style().layoutSpacing(QtGui.QSizePolicy.PushButton,
                                               QtGui.QSizePolicy.PushButton,
                                               QtCore.Qt.Horizontal)
            spaceY = self.spacing() + \
                     wid.style().layoutSpacing(QtGui.QSizePolicy.PushButton,
                                               QtGui.QSizePolicy.PushButton,
                                               QtCore.Qt.Vertical)
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()
        
if __name__ == "__main__":
    main()
