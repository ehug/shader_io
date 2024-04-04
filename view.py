#==================================================================================================#
# Shader IO
#
# Purpose: To export and import shaders as separate files and
#          apply them to objects in the current scene.
#
# Dependencies: 
#               PySide2
#
#
# Author: Eric Hug
# Updated: 4/03/2024
'''
# Example Code:
from importlib import reload
from shader_io import view
reload(view)
view.start_up()
'''
#==================================================================================================#
# IMPORT
# built-in python libraries
import sys
import json
import logging
from importlib import reload

# 3rd-party
from maya import cmds
from maya import OpenMayaUI
from PySide2 import QtWidgets, QtCore
from shiboken2 import wrapInstance

from shader_io import core
reload(core)

#==================================================================================================#
# VARIABLES
LOG = logging.getLogger(__name__)

#==================================================================================================#
# FUNCTIONS
def start_up(width=1080, height=500):
    '''Start Function for user to run the tool.'''
    win = get_maya_main_window()
    for each in win.findChildren(QtWidgets.QWidget):
        if each.objectName() == "ShaderIO":
            each.deleteLater()
    tool = ShaderIO(parent=win)
    tool.resize(width, height)
    tool.show()

    return tool

def get_maya_main_window():
    '''Locates Main Window, so we can parent our tool to it.'''
    maya_window_ptr = OpenMayaUI.MQtUtil.mainWindow()

    return wrapInstance(interpret_int_long(maya_window_ptr), QtWidgets.QWidget)

def interpret_int_long(value):
    if int(sys.version.split(" ")[0][0]) > 2:
        return int(value)
    else:
        return long(value)

#==================================================================================================#
# CLASSES
class ShaderIO(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ShaderIO, self).__init__(parent=parent)
        # ----------- #
        # Base Window #
        # ----------- #
        self.setWindowTitle("Shader IO")
        self.setObjectName("ShaderIO")
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setSpacing(6)
        self.setLayout(self.main_layout)
        # ------------------ #
        # File Browse Widget #
        # ------------------ #
        # # Components
        self.browse_widget = BasicWidget(layout_type="horizontal", 
                                         spacing=6)
        self.browse_label = QtWidgets.QLabel("File Path:")
        self.browse_textfield = QtWidgets.QLineEdit()
        self.browse_btn = QtWidgets.QPushButton("Browse")
        # # Assemble Widget
        self.browse_widget.layout.addWidget(self.browse_label)
        self.browse_widget.layout.addWidget(self.browse_textfield)
        self.browse_widget.layout.addWidget(self.browse_btn)
        # # Component Settings
        self.browse_btn.clicked.connect(self.browse_command)
        # ------- #
        # Divider #
        # ------- #
        self.divider = QtWidgets.QFrame()
        self.divider.setLineWidth(0)
        self.divider.setFrameShape(QtWidgets.QFrame.HLine)
        # --------------------- #
        # Export Options Widget #
        # --------------------- #
        # # Components
        self.options_widget = BasicWidget(layout_type="vertical", 
                                          spacing=6)
        self.options_header_label = QtWidgets.QLabel("Export Options")
        self.options_label = QtWidgets.QLabel("Selection Method:")
        self.options_se_rbtn = QtWidgets.QRadioButton("Shading Groups")
        self.options_m_rbtn = QtWidgets.QRadioButton("Meshes")
        # # Assemble Widget
        self.options_widget.layout.addWidget(self.options_header_label)
        self.options_widget.layout.addWidget(self.options_label)
        self.options_widget.layout.addWidget(self.options_se_rbtn)
        self.options_widget.layout.addWidget(self.options_m_rbtn)
        # # Component Settings
        self.options_header_label.setAlignment(QtCore.Qt.AlignHCenter)
        self.options_m_rbtn.setChecked(True)
        # ---------------------- #
        # Import/ Export Buttons #
        # ---------------------- #
        # # Components
        self.io_widget = BasicWidget(layout_type="horizontal", 
                                     spacing=6)
        self.io_import_btn = QtWidgets.QPushButton("Import")
        self.io_export_btn = QtWidgets.QPushButton("Export")
        # # Assemble Widget
        self.io_widget.layout.addWidget(self.io_import_btn)
        self.io_widget.layout.addWidget(self.io_export_btn)
        # # Component Settings
        self.io_import_btn.clicked.connect(self.import_command)
        self.io_export_btn.clicked.connect(self.export_command)
        # ------------------------- #
        # Output Import Code Widget #
        # ------------------------- #
        # # Components
        self.out_import_widget = BasicWidget(layout_type="vertical", 
                                             spacing=6)
        self.out_import_label = QtWidgets.QLabel("Corresponding Import Code (After Export):")
        self.out_import_textfield = QtWidgets.QTextEdit()
        # # Assemble Widget
        self.out_import_widget.layout.addWidget(self.out_import_label)
        self.out_import_widget.layout.addWidget(self.out_import_textfield)
        self.out_import_textfield.setStyleSheet("{font: 24pt Courier; color: lightgrey; font-size: 10pt;}")
        # ----------------------------------------- #
        # Put SubComponents together in main widget #
        # ----------------------------------------- #
        self.main_layout.addWidget(self.browse_widget)
        self.main_layout.addWidget(self.divider)
        self.main_layout.addWidget(self.options_widget)
        self.main_layout.addWidget(self.io_widget)
        self.main_layout.addWidget(self.out_import_widget)
        # -------- #
        # Finalize #
        # -------- #
        self.setWindowFlags(QtCore.Qt.Window)


    def browse_command(self):
        '''When Browse Button pressed, allows user to select a json file,
           and returns full file path to the browse textfield.
        '''
        self.file_path = QtWidgets.QFileDialog.getSaveFileName(self,
                                                              caption="get file",
                                                              filter="JSON Files (*.json)")
        new_string = list(self.file_path)
        new_string.pop(-1)
        new_string = str(new_string).replace("[", "").replace("]", "").replace("\'", "").replace("\"", "")
        self.browse_textfield.setText(new_string)

    def import_command(self):
        with open(self.browse_textfield.text()) as json_file:
            json_data = json.load(json_file)
        shaders_dict = json_data
        conflicts_list = []
        conflict_resolution = "rename"
        shaders_list = list(shaders_dict.keys())
        for each in shaders_list:
            if each in cmds.ls(type="shadingEngine"):
                conflicts_list.append(each)
        if len(conflicts_list) > 0:
            self.popup_widget = ShaderNameConflictsDialog(parent=self,
                                                          file_path=self.browse_textfield.text())
            # self.popup_widget.setParent(self)
            self.popup_widget.move(self.width()+ self.x(), self.y())
            self.popup_widget.show()
        else:
            core.import_shaders(importPath=self.browse_textfield.text(), shader_conflicts=conflict_resolution)
    
    def export_command(self):
        if self.options_m_rbtn.isChecked():
            core.export_shaders(full_export_path=self.browse_textfield.text(), 
                                selection_type="mesh")
        else:
            core.export_shaders(full_export_path=self.browse_textfield.text(), 
                                selection_type="shadingEngine")
        import_code_string = "# Note: This import method will create renamed duplicate shaders in scene if naming conflicts exist.\n"\
                             "#            To change, replace the argument of shader_conflicts from \"rename\" to \"skip\" or \"replace\".\n"\
                             "#\n"\
                             "# --- Code Below --- #\n"\
                             "from importlib import reload\n"\
                             "from shader_io import core\n"\
                             "reload(core)\n"\
                             "core.import_shaders(importPath=\"{}\",\n"\
                             "	                 shader_conflicts=\"rename\")".format(self.browse_textfield.text())
        self.out_import_textfield.setText(import_code_string)


class BasicWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, layout_type="vertical", spacing=0, margins=[0,0,0,0], h_align="left", v_align="top"):
        '''Creates a widget that acts a base template for other tools to build from.
            Parameters:
                        parent:      The parent widget to attach this widget to. 
                                        Helpful for connecting widget to an application's main window, like Maya. 
                                        Otherwise, leave as None.
                        layout_type: How items are place in the widget's layout.
                                        values: "vertical", "horizontal", "grid"
                        spacing:     Space between other UI components inside this widget.

                        margins:     Border space around all for sides of the widget. 
                                        [left, top, right, bottom]
                        h_align:     Horizontal alignment of items.
                                        values: "left", "center", "right"
                        v_align:     Vertical alignment of items. 
                                        values: "top", "center", "bottom"
        '''
        super(BasicWidget, self).__init__(parent=parent)
        # self.setStyleSheet(STYLESHEET)
        self.layout_type = layout_type
        self.h_align = h_align
        self.v_align = v_align
        self.spacing = spacing
        self.margins = QtCore.QMargins(margins[0], margins[1], margins[2], margins[3])

        # Base Window
        # # Layout Type
        if self.layout_type == "vertical":
            self.layout = QtWidgets.QVBoxLayout()
        elif self.layout_type == "horizontal":
            self.layout = QtWidgets.QHBoxLayout()
        elif self.layout_type == "grid":
            self.layout = QtWidgets.QGridLayout()
        else:
            LOG.error("Invalid Layout Argument: \'{}\'".format(self.layout_type))
        self.setLayout(self.layout)
        # # Layout Alignments:
        # # # Horizontal
        if self.h_align == "left":
            self.layout.setAlignment(QtCore.Qt.AlignLeft)
        elif self.h_align == "center":
            self.layout.setAlignment(QtCore.Qt.AlignHCenter)
        elif self.h_align == "right":
            self.layout.setAlignment(QtCore.Qt.AlignRight)
        else:
            LOG.error("Invalid Horizontal Alignment Argument (\'h_align\'): \'{}\'".format(self.h_align))
        # # # Vertical
        if self.v_align == "top":
            self.layout.setAlignment(QtCore.Qt.AlignTop)
        elif self.v_align == "center":
            self.layout.setAlignment(QtCore.Qt.AlignVCenter)
        elif self.v_align == "bottom":
            self.layout.setAlignment(QtCore.Qt.AlignBottom)
        else:
            LOG.error("Invalid Vertical Alignment Argument (\'v_align\'): \'{}\'".format(self.v_align))
        # # Spacing
        self.layout.setSpacing(self.spacing)
        self.layout.setContentsMargins(self.margins)

class ShaderNameConflictsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, file_path=""):
        '''
        Popup Window that appears if naming conflicts arise while importing data
        '''
        super(ShaderNameConflictsDialog, self).__init__(parent=parent)
        self.file_path = file_path
        self.message_text = '''One or more shaders in the imported file already exist in this scene. \nWhat would you like to do?'''
        self.rename_text = "Copy"
        self.skip_text = "Skip"
        self.replace_text = "Replace"
        self.cancel_text = "cancel"
        # UI Components
        self.main_layout = QtWidgets.QVBoxLayout()
        self.button_widget = BasicWidget(layout_type="horizontal", 
                                         spacing=6)
        self.message_label = QtWidgets.QLabel(self.message_text)
        self.duplicate_btn = QtWidgets.QPushButton(self.rename_text)
        self.skip_btn = QtWidgets.QPushButton(self.skip_text)
        self.replace_btn = QtWidgets.QPushButton(self.replace_text)
        self.cancel_btn = QtWidgets.QPushButton(self.cancel_text)
        # Assemble Components
        self.setLayout(self.main_layout)
        self.main_layout.addWidget(self.message_label)
        self.main_layout.addWidget(self.button_widget)
        self.button_widget.layout.addWidget(self.duplicate_btn)
        self.button_widget.layout.addWidget(self.skip_btn)
        self.button_widget.layout.addWidget(self.replace_btn)
        self.button_widget.layout.addWidget(self.cancel_btn)
        # Component Settings
        self.message_label.setAlignment(QtCore.Qt.AlignHCenter)
        self.duplicate_btn.clicked.connect(self.resolve_conflict)
        self.skip_btn.clicked.connect(self.resolve_conflict)
        self.replace_btn.clicked.connect(self.resolve_conflict)
        self.cancel_btn.clicked.connect(self.resolve_conflict)
        # Finalize
        self.resize(200, 100)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowFlags(QtCore.Qt.Dialog)
        self.setWindowTitle('Shader Naming Conflict Found')
        self.show()
    
    def resolve_conflict(self):
        '''Determine how to deal with existing shaders with matching names'''
        if self.sender().text() == self.rename_text:
            self.method = "rename"
            core.import_shaders(importPath=self.file_path, shader_conflicts=self.method)
        elif self.sender().text() == self.skip_text:
            self.method = "skip"
            core.import_shaders(importPath=self.file_path, shader_conflicts=self.method)
        elif self.sender().text() == self.replace_text:
            self.method = "replace"
            core.import_shaders(importPath=self.file_path, shader_conflicts=self.method)
        else:
            self.method = "cancel"
            core.import_shaders(importPath=self.file_path, shader_conflicts=self.method)
        self.accept()

