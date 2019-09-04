import os
import sys
import copy
import argparse
import signal

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
from PyQt5 import QtGui                      # pylint: disable=F0401
from PyQt5.QtWidgets import QAbstractItemView    # pylint: disable=F0401
from PyQt5.QtGui import QIcon                # pylint: disable=F0401
from PyQt5.QtCore import pyqtSlot            # pylint: disable=F0401

from concurrent.futures import ThreadPoolExecutor
from threading import current_thread

import yt2mp3
import yt2mp3_utils

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
        self.thread_pool = ThreadPoolExecutor(max_workers=max(1, os.cpu_count()-1))


        ###############################
        # set up layout of main window
        ###############################

        # first, some buttons to the right
        self.add_tab_button = QPushButton('+ Tab')          # button for adding new tabs (see below)
        self.run_all_jobs_button = QPushButton('Run all')   # button to run all runnable (not yet running and un-run) jobs
        self.stop_all_jobs_button = QPushButton('Stop all') # button to terminate all running jobs

        self.button_panel = QWidget()                       # widget and layout to group buttons
        button_layout = QVBoxLayout(self)

        button_layout.addWidget(self.add_tab_button)        # assemble buttons
        button_layout.addStretch()                          # add some spacing
        button_layout.addWidget(self.run_all_jobs_button)
        button_layout.addWidget(self.stop_all_jobs_button)
        self.button_panel.setLayout(button_layout)

        # second, a tab panel for job specification to the left
        self.tab_panel = QTabWidget()
        self.tab_panel.setTabsClosable(True)                # make tabs closable.
        self.tabs_created = 0                               # count how many tabs have been created

        # assemble gui elements
        window_layout = QHBoxLayout(self)
        window_layout.addWidget(self.tab_panel)             # tab panel to the left
        window_layout.addWidget(self.button_panel)          # controls to the right
        self.setLayout(window_layout)

        # add initial tab from argparse_namespace input and show
        self.add_tab()

        ################################
        # add functionality and controls
        ################################
        self.add_tab_button.clicked.connect(self.add_tab)
        self.tab_panel.tabCloseRequested.connect(self.close_tab)
        self.run_all_jobs_button.clicked.connect(self.run_all_jobs)
        self.stop_all_jobs_button.clicked.connect(self.stop_all_jobs)


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

        new_tab = JobPanel(self.thread_pool, argparse_namespace)
        new_tab_name = 'Job {}'.format(self.tabs_created)

        self.tab_panel.addTab(new_tab, new_tab_name)
        self.tabs_created += 1

        self.tab_panel.setCurrentIndex(active_tab_index+1)

    def close_tab(self, index):
        """
        Removes JobTab, its data and kills its job (if running)
        """
        # TODO: figure out what to do. what if job is running? just blindly kill thread?
        self.tab_panel.widget(index).stop_job_callback_fxn()
        self.tab_panel.removeTab(index)

    def run_all_jobs(self):
        """
        Attempts to run all jobs in the job panel
        """
        for i in range(len(self.tab_panel)):
            self.tab_panel.widget(i).run_job_callback_fxn()

    def stop_all_jobs(self):
        """
        Attempts to stop all jobs in the job panel
        """
        for i in range(len(self.tab_panel)):
            self.tab_panel.widget(i).stop_job_callback_fxn()

    def closeEvent(self, event):
        self.stop_all_jobs()
        self.thread_pool.shutdown(wait=False)
        event.accept()


class JobPanel(QWidget):
    """
    A Widget class representing all information required for executing
    a download+conversion job
    """

    def __init__(self, thread_pool, argparse_namespace):
        """
        Constitutes a GUI container for job information and execution.
        Holds the necessary data, allows editing of parameters.

        Parameters:
        -----------
        thread_pool: multiprocessing.Pool - Executor for running jobs.

        argparse_namespace: argparse.Namespace - container for job data
        """
        super(QWidget, self).__init__()

        # use this ThreadPoolExecutor instance for executing jobs
        self.thread_pool = thread_pool
        # use this argparse.Namespace instance for job data specification
        self.argparse_namespace = argparse_namespace
        # use this to keep track of all created subprocess (in case they need killin')
        # yt2mp3.download_convert_split provides an interface for that list.
        self.child_processes = []
        self.worker_thread = None


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

        ##############
        # assemble tab
        ##############
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

        ################################
        # add functionality and controls
        ################################
        # TODO: choose output button (change output location field!)
        self.run_job_button.clicked.connect(self.run_job_callback_fxn)
        self.stop_job_button.clicked.connect(self.stop_job_callback_fxn)

        self.video_id_url_input.textChanged.connect(self.parse_video_id_url_callback_fxn)
        self.output_location_input.textChanged.connect(self.parse_output_location_callback_fxn)

        self.segment_output_checkbox.toggled.connect(self.segment_output_state_changed_callback_fxn)
        self.output_segment_duration_input.textChanged.connect(self.parse_output_segment_length_callback_fxn)
        self.output_segment_name_pattern_input.textChanged.connect(self.parse_output_name_pattern_callback_fxn)

        self.output_location_dialog_button.clicked.connect(self.select_output_location_from_qfiledialog_callback_fxn)

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

    def parse_video_id_url_callback_fxn(self):
        """
        Attempts to parse video URL output fiel and add its value to self.argparse_namespace
        """
        # NOTE: self.argparse_namespace is a list of strings!
        text = self.video_id_url_input.text()
        if len(self.argparse_namespace.video) == 0:
            self.argparse_namespace.video.append(text)
        else:
            self.argparse_namespace.video[0] = text

    def parse_output_location_callback_fxn(self):
        """
        Attempts to parse output path
        """
        self.argparse_namespace.output = self.output_location_input.text()

    def select_output_location_from_qfiledialog_callback_fxn(self):
        """
        Opens a file (right now really only a directory) selection dialogue.
        Allows to browser for an output location (directory).

        To specify a file name, add it manually, until a suitable solution has been found.
        """

        # TODO: Use a file selectinon dialog which is able to select both files or folders! any found examples so far failed!
        # TODO: Improve user experience in general
        dialog = QFileDialog(self, 'Pick output directory')
        dialog.setFileMode(QFileDialog.Directory)

        if dialog.exec_() == 1:
            output_dir = dialog.selectedFiles()[0]
            self.output_location_input.setText(output_dir)
            # NOTE: triggers self.output_location_input.textChanged





    def segment_output_state_changed_callback_fxn(self):
        """
        Activates/deactivates output segmentation parameter fields according to checkbox state
        """
        box_is_checked = self.segment_output_checkbox.isChecked()
        self.output_segment_duration_input.setEnabled(box_is_checked)
        self.output_segment_name_pattern_input.setEnabled(box_is_checked)

        if box_is_checked:
            self.parse_output_segment_length_callback_fxn()
        else:
            self.argparse_namespace.segment_length = None



    def parse_output_segment_length_callback_fxn(self):
        """
        Attempts to parse the length of the output segments
        """

        text = self.output_segment_duration_input.text()
        if text:
            try:
                self.argparse_namespace.segment_length = int(text)
            except ValueError:
                # TODO: properly take care of this. Write error message to self.output_window
                # TODO: In general think about whether there might be a better solution than manual parsing.
                pass
        else:
            self.argparse_namespace.segment_length = None


    def parse_output_name_pattern_callback_fxn(self):
        """
        Attempts to parse the output name pattern for segmented mp3 files
        """
        self.argparse_namespace.segment_name = self.output_segment_name_pattern_input.text()

    def run_job_function(self):
        """
        Container function for submission to self.thread_pool
        holding all necessary functionality for runnanle and stoppable job treads
        """
        # TODO: capture stdout + stderr, redirect to self.output_window (needs to happen earlier, upon tab creation)
        # TODO: write stderr/stdout into qtextwindowthing
        self.worker_thread = current_thread()

        # below line collects started threads to the self.child_processes list
        yt2mp3_utils.check_requirements()
        yt2mp3.download_convert_split(self.argparse_namespace, self)

        # TODO: gui stuff:
        #   unlock stop button
        #   lock param input stuff.
        #   once done, unlock gui stuff again.
        #   write nice status updates (idle/waiting/running/done))


    def run_job_callback_fxn(self):
        """
        Try to run this JobPanel's job according to parameterization
        """
        self.thread_pool.submit(self.run_job_function)


    def stop_job_callback_fxn(self):
        """
        Try to stop this JobPanel's job according to parameterization
        """

        # TODO: disable output window
        # TODO: unlock input fields and buttons.

        for p in self.child_processes:
            print('KILLING CHILD PROCESS', p)
            p.kill()

        self.child_processes = []
        self.worker_thread = None
