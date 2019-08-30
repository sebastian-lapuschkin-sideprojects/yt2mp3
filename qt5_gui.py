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
from PyQt5.QtGui import QIcon                # pylint: disable=F0401
from PyQt5.QtCore import pyqtSlot            # pylint: disable=F0401

import yt2mp3

# entry hook(s) for the gui app.
# planned use:
# import <this_module>
# <this_module>.run()
def run():
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())


class MainWindow(QWidget):
    def __init__(self):
        # TODO add input param args_namespace containing data of first tab
        # set up basic geometry of main window
        super().__init__()
        self.title = 'yt2mp3 - Your simple Youtube to MP3 converter'
        self.left = 0
        self.top = 0
        self.width = 600
        self.height = 300
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # set up layout of main window
        # left: tab widget with jobs
        self.tab_panel = JobTabPanel()
        #self.tab_panel = None

        # right: button bar with global controls.
        # TODO. global controls might need access to tabs.
        # TODO: give ThreadPoolExecutor to main window, or tab panel
        # TODO: connect controls
        self.button_panel = ButtonPanel(self.tab_panel)

        # TODO: find out how to specify for each widget how much space it may use
        # QWidget.resize(...) doesnt do anything.

        #self.setCentralWidget(self.button_panel)
        window_layout = QHBoxLayout(self)
        window_layout.addWidget(self.tab_panel)
        window_layout.addWidget(self.button_panel)
        self.setLayout(window_layout)
        self.show()




class ButtonPanel(QWidget):
    def __init__(self, job_tab_panel):
        super(QWidget, self).__init__()

        #TODO: use unused space to show overall job status?

        # a button to add a new JobTab to the JobTabPanel
        # TODO: add functionality. # TODO: replace + with icon?
        self.add_tab_button = QPushButton('+')

        # a button to run all runnable (not yet running and un-run) jobs
        # TODO: add functionality. # TODO: replace with icon?
        self.run_all_jobs_button = QPushButton('>>')

        # a button to terminate all running jobs
        # TODO: add functionality. # TODO: replace with icon?
        self.kill_all_jobs_button = QPushButton('XX')

        buttons_layout = QVBoxLayout(self)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.add_tab_button)
        buttons_layout.addWidget(self.run_all_jobs_button)
        buttons_layout.addWidget(self.kill_all_jobs_button)
        self.setLayout(buttons_layout)



class JobTabPanel(QWidget):
    #TODO how to get get rid of/suppress this weird add-layout-message? message?

    def __init__(self):
        super(QWidget, self).__init__()

        # Initialize tab screen.
        # self.tabs contains all existing tabs
        self.tabs = QTabWidget()

        # allows tabs to be closed (should, but doesnt.)
        # TODO: fix! # TODO: make sure all tab data (job data) is removed/cleaned up properly
        self.tabs.setTabsClosable(True)
        self.tabs_created = 0

        # create the initial tab.
        self.add_tab()

        # Add tabs to widget
        panel_layout = QVBoxLayout(self)
        panel_layout.addWidget(self.tabs)
        self.setLayout(panel_layout)
        #NOTE: apparently widgets can have layouts and layouts are containers to widgets

        #self.tabs.resize(width,height)# NOTE RESETS TAB PANEL GEOMETRY? Does not seeem to be required (with the jobtabs as the only widget)
        self.tabs.resize(100,100)

    def run_tab_job(self):
        # NOTE: this line parses the command line args as given. probably default values.
        # this could be used for populating the tab values upon creation
        args = yt2mp3.parse_command_line_args()

        # for now, only prints the args given on command line.
        # TODO: print the tab-specific args.
        print(args)


    def add_tab(self):
        """
        Adds a new tab to the JobTabPanel
        """
        new_tab = QWidget() #TODO create specialized tab class (?).
        tab_name = 'Tab {}'.format(self.tabs_created)
        tab_layout = QVBoxLayout(self)

        # TODO: add proper gui stuff with controls here.
        # that includes text fields for params, etc
        # Idea: upon adding a tab, copy settings from most recently looked at/highest numbered tab (if there is one)
        # Idea: each tab has a argparse.Namespace object containing that info.
        # Idea: when entering new data. use yt2mp3.parse_command_line_args to update the data info and display if successful.
        # below is first dummy code for playing around

        # register fxn to add a tab to this button# TODO: this fxn should be registered in the control button panel
        new_tab_button = QPushButton('Add new tab from tab {}'.format(self.tabs_created))
        new_tab_button.clicked.connect(self.add_tab)

        # register fxn to run passed command line args
        # TODO: finish, ie register namespace for command line options
        run_process_button = QPushButton('Run stuff from tab {}'.format(self.tabs_created))
        run_process_button.clicked.connect(self.run_tab_job)

        tab_layout.addWidget(new_tab_button)
        tab_layout.addWidget(run_process_button)

        new_tab.setLayout(tab_layout)
        self.tabs.addTab(new_tab, tab_name)
        self.tabs_created += 1
