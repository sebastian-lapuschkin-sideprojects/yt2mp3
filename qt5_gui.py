import os
import sys

from PyQt5.QtWidgets import QMainWindow      # pylint: disable=F0401
from PyQt5.QtWidgets import QApplication     # pylint: disable=F0401
from PyQt5.QtWidgets import QPushButton      # pylint: disable=F0401
from PyQt5.QtWidgets import QWidget          # pylint: disable=F0401
from PyQt5.QtWidgets import QAction          # pylint: disable=F0401
from PyQt5.QtWidgets import QTabWidget       # pylint: disable=F0401
from PyQt5.QtWidgets import QVBoxLayout      # pylint: disable=F0401
from PyQt5.QtWidgets import QHBoxLayout      # pylint: disable=F0401
from PyQt5.QtWidgets import QVBoxLayout      # pylint: disable=F0401
from PyQt5.QtWidgets import QLabel           # pylint: disable=F0401
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
        self.height = 300
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)


        ###################################################################################
        # set up threading work backend, leaving at least one cpu for the OS and other crap
        ###################################################################################
        self.thread_pool_executor = ThreadPoolExecutor(max_workers=max(1,os.cpu_count()-1))

        ###############################
        # set up layout of main window
        ###############################

        # first, some buttons to the right
        self.add_tab_button = QPushButton('+')         # button for adding new tabs (see below)
        self.run_all_jobs_button = QPushButton('>>')   # button to run all runnable (not yet running and un-run) jobs
        self.kill_all_jobs_button = QPushButton('XX')  # button to terminate all running jobs

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
        self.show()

        #TODO: add functionality and controls


    def add_tab(self):
        """
        Adds a new tab to the JobTabPanel
        """
        new_tab_content = JobPanel(self.thread_pool_executor, yt2mp3.parse_command_line_args()) #TODO infer number of active/existing tabs. set argparse_namespace
        tab_name = 'Tab {}'.format(self.tabs_created)
        #tab_layout = QVBoxLayout()

        # TODO: add proper gui stuff with controls here.
        # that includes text fields for params, etc
        # Idea: upon adding a tab, copy settings from most recently looked at/highest numbered tab (if there is one)
        # Idea: each tab has a argparse.Namespace object containing that info.
        # Idea: when entering new data. use yt2mp3.parse_command_line_args to update the data info and display if successful.
        # below is first dummy code for playing around

        # register fxn to add a tab to this button# TODO: this fxn should be registered in the control button panel
        ##new_tab_button = QPushButton('Add new tab from tab {}'.format(self.tabs_created))
        ##new_tab_button.clicked.connect(self.add_tab)

        # register fxn to run passed command line args
        # TODO: finish, ie register namespace for command line options
        ##run_process_button = QPushButton('Run stuff from tab {}'.format(self.tabs_created))
        #run_process_button.clicked.connect(self.run_tab_job)

        ##tab_layout.addWidget(new_tab_button)
        ##tab_layout.addWidget(run_process_button)

        ##new_tab.setLayout(tab_layout)
        self.tab_panel.addTab(new_tab_content, tab_name)
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
        video_id_url_label = QLabel('URL/ID')


        # assemble Panel
        layout = QHBoxLayout()
        layout.addWidget(video_id_url_label)
        self.setLayout(layout)

        #TODO: add functionality and controls





    def run_tab_job(self):
        # TODO: refactor
        # NOTE: this line parses the command line args as given. probably default values.
        # this could be used for populating the tab values upon creation
        args = yt2mp3.parse_command_line_args()

        # for now, only prints the args given on command line.
        # TODO: print the tab-specific args.
        print(args)



