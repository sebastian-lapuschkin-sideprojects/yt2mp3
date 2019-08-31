import os
import sys
import copy
import argparse

from PyQt5.QtWidgets import QMainWindow      # pylint: disable=F0401
from PyQt5.QtWidgets import QApplication     # pylint: disable=F0401
from PyQt5.QtWidgets import QPushButton      # pylint: disable=F0401
from PyQt5.QtWidgets import QWidget          # pylint: disable=F0401
from PyQt5.QtWidgets import QAction          # pylint: disable=F0401
from PyQt5.QtWidgets import QTabWidget       # pylint: disable=F0401
from PyQt5.QtWidgets import QVBoxLayout      # pylint: disable=F0401
from PyQt5.QtWidgets import QHBoxLayout      # pylint: disable=F0401
from PyQt5.QtWidgets import QGridLayout      # pylint: disable=F0401
from PyQt5.QtWidgets import QLabel           # pylint: disable=F0401
from PyQt5.QtWidgets import QLineEdit        # pylint: disable=F0401
from PyQt5.QtWidgets import QCheckBox        # pylint: disable=F0401
from PyQt5.QtWidgets import QFileDialog      # pylint: disable=F0401
from PyQt5.QtWidgets import QPlainTextEdit   # pylint: disable=F0401
from PyQt5.QtGui import QIcon                # pylint: disable=F0401
from PyQt5.QtCore import pyqtSlot            # pylint: disable=F0401

from concurrent.futures import ThreadPoolExecutor
import yt2mp3

# entry hook for the gui app.
# planned use:
# import <this_module>
# <this_module>.run()
def run():
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())


class MainWindow(QWidget):
    def __init__(self):
        # set up basic geometry of main window
        super().__init__()
        self.title = 'yt2mp3 - Your simple Youtube to MP3 converter'
        self.left = 0
        self.top = 0
        self.width = 600
        self.height = 350
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)


        ###################################################################################
        # set up threading work backend, leaving at least one cpu for the OS and other crap
        ###################################################################################
        self.thread_pool_executor = ThreadPoolExecutor(max_workers=max(1,os.cpu_count()-1))
        # TODO: or better use QThread? check features!

        ###############################
        # set up layout of main window
        ###############################

        # first, some buttons to the right
        self.add_tab_button = QPushButton('+ Tab')         # button for adding new tabs (see below)
        self.run_all_jobs_button = QPushButton('Run all')   # button to run all runnable (not yet running and un-run) jobs
        self.kill_all_jobs_button = QPushButton('Stop all')  # button to terminate all running jobs

        self.button_panel = QWidget()                 # widget and layout to group buttons
        button_layout = QVBoxLayout(self)

        button_layout.addWidget(self.add_tab_button)   # assemble buttons
        button_layout.addStretch()                     # add some spacing
        button_layout.addWidget(self.run_all_jobs_button)
        button_layout.addWidget(self.kill_all_jobs_button)
        self.button_panel.setLayout(button_layout)

        # second, a tab panel for job specification to the left
        self.tab_panel = QTabWidget()
        self.tab_panel.setTabsClosable(True)           # make tabs closable. TODO: FIX! does not do anything
        self.tabs_created = 0                          # count how many tabs have been created

        # assemble gui elements
        window_layout = QHBoxLayout(self)
        window_layout.addWidget(self.tab_panel)        # tab panel to the left
        window_layout.addWidget(self.button_panel)     # controls to the right
        self.setLayout(window_layout)

        # add initial tab from argparse_namespace input and show
        self.add_tab()

        ################################
        # add functionality and controls
        ################################

        #TODO: run all, stop all, close tab
        self.add_tab_button.clicked.connect(self.add_tab)

        self.show()


    def add_tab(self):
        """
        Adds a new tab to the JobTabPanel
        """
        active_tab_index = self.tab_panel.currentIndex()
        if active_tab_index >= 0:
            argparse_namespace = self.tab_panel.widget(active_tab_index).get_args()
        else:
            argparse_namespace = yt2mp3.parse_command_line_args()

        new_tab = JobPanel(self.thread_pool_executor, argparse_namespace)
        new_tab_name = 'Tab {}'.format(self.tabs_created)



        self.tab_panel.addTab(new_tab, new_tab_name)
        self.tabs_created += 1


class JobPanel(QWidget):
    """
    A Widget class representing all information required for executing
    a download+conversion job
    """

    def __init__(self, thread_pool_executor, argparse_namespace):
        """
        Constitutes a GUI container for job information and execution.
        Holds the necessary data, allows editing of parameters.

        Parameters:
        -----------
        thread_pool_executor: concurrent.futures.ThreadPoolExecutor - Executor for running jobs.

        argparse_namespace: argparse.Namespace - container for job data
        """
        super(QWidget, self).__init__()

        # use this ThreadPoolExecutor instance for executing jobs
        self.thread_pool_executor = thread_pool_executor
        # use this argparse.Namespace instance for job data specification
        self.argparse_namespace = argparse_namespace

        ################################
        # set up tab elements and layout
        ################################

        # per argument (video, output, segment length, segment name):
        # we need QLabel to specify the kind of information shown
        # an option to enter that information as QTextEdit/QFileDialog
        # controls and feedback (QPlainTextEdit, setReadOnly(True)) for this one job.

        # create gui elements and populate with default values from self.argparse_namespace
        self.video_id_url_label = QLabel('URL/ID')
        self.video_id_url_input = QLineEdit()
        self.video_id_url_input.setText(argparse_namespace.video[0] if argparse_namespace.video else '')

        self.output_location_label = QLabel('Output location')
        self.output_location_input = QLineEdit()
        self.output_location_input.setText(argparse_namespace.output)
        self.output_location_dialog_button = QPushButton('Choose...')

        self.segment_output_label = QLabel('Split output into segments')
        self.segment_output_checkbox = QCheckBox()
        self.segment_output_checkbox.setChecked(self.argparse_namespace.segment_length is not None )

        self.output_segment_duration_label = QLabel('Output segment duration')
        self.output_segment_duration_input = QLineEdit()
        self.output_segment_duration_input.setEnabled(self.segment_output_checkbox.isChecked())
        self.output_segment_duration_label.setEnabled(self.segment_output_checkbox.isChecked())
        self.output_segment_duration_input.setText(str(self.argparse_namespace.segment_length).replace('None',''))

        self.output_segment_name_pattern_label = QLabel('Segment name pattern')
        self.output_segment_name_pattern_input = QLineEdit()
        self.output_segment_duration_label.setEnabled(self.segment_output_checkbox.isChecked())
        self.output_segment_name_pattern_input.setEnabled(self.segment_output_checkbox.isChecked())
        self.output_segment_name_pattern_input.setText(self.argparse_namespace.segment_name)

        self.output_window_label = QLabel('Process output')
        self.output_window = QPlainTextEdit()  # TODO: subclass this, reroute stdout. or remove https://stackoverflow.com/questions/14161100/which-qt-widget-should-i-use-for-message-display
        self.output_window.setEnabled(False)

        self.run_job_button = QPushButton('Run')
        self.stop_job_button = QPushButton('Stop')
        # NOTE: this is how to obtain the entered text
        #def test():
        #    print('Text changed to "{}""'.format(self.video_id_url_input.text()))
        #self.video_id_url_input.textChanged.connect(test)

        # add initial values form self.argparse_namespace


        # assemble tab
        layout = QGridLayout()

        layout.addWidget(self.video_id_url_label, 0, 0)
        layout.addWidget(self.video_id_url_input, 0, 1)

        layout.addWidget(self.output_location_label, 1, 0)
        layout.addWidget(self.output_location_input, 1, 1)
        layout.addWidget(self.output_location_dialog_button, 1, 2)

        layout.setRowStretch(2,1)  # allows the constructio of "empty lines"

        layout.addWidget(self.segment_output_label, 3, 0)
        layout.addWidget(self.segment_output_checkbox, 3, 1)

        layout.addWidget(self.output_segment_duration_label, 4, 0)
        layout.addWidget(self.output_segment_duration_input, 4, 1)

        layout.addWidget(self.output_segment_name_pattern_label, 5, 0)
        layout.addWidget(self.output_segment_name_pattern_input, 5, 1)

        layout.addWidget(self.run_job_button, 4, 2)
        layout.addWidget(self.stop_job_button, 5, 2)

        layout.setRowStretch(6,1)

        layout.addWidget(self.output_window_label, 7, 0)
        layout.addWidget(self.output_window, 8, 0, 1, 3)
        layout.setRowStretch(8, 2)  # make output text box two rows high

        self.setLayout(layout)      # install GUI elements

        #TODO: add functionality and controls


    def get_args(self, copy=True):
        """
        Returns the argparse.Namespace object of this JobPanel instance

        Parameters:
        -----------
        copy: bool - (optional). Default:True . Controls wheter to return a
            copy or a reference to the argparse.Namespace object

        Returns:
        --------
        argparse.Namespace containing this JobPanel's configuration
        """
        if copy:
            return argparse.Namespace(**vars(self.argparse_namespace))
        else:
            return self.argparse_namespace



    def run_job(self):
        # TODO: refactor
        # NOTE: this line parses the command line args as given. probably default values.
        # this could be used for populating the tab values upon creation
        args = yt2mp3.parse_command_line_args()

        # for now, only prints the args given on command line.
        # TODO: print the tab-specific args.
        print(args)



