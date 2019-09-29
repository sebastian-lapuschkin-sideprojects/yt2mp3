import os
import sys
import copy
import argparse
import signal
import time

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
from PyQt5.QtGui import QTextCursor          # pylint: disable=F0401
from PyQt5.QtCore import pyqtSlot            # pylint: disable=F0401
from PyQt5.QtCore import QObject             # pylint: disable=F0401
from PyQt5.QtCore import pyqtSignal

from concurrent.futures import ThreadPoolExecutor
from threading import current_thread
from threading import Thread

import yt2mp3
import yt2mp3_utils

from .job_panel import JobPanel
from .process_output_monitor import ProcessOutputMonitor

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
        self.width = 900
        self.height = 385
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        ###################################################################################
        # set up threading work backend, leaving at least one cpu for the OS and other crap
        ###################################################################################
        self.worker_thread_pool = ThreadPoolExecutor(max_workers=max(1, os.cpu_count()-1))
        self.gui_communicator_thread_pool = ThreadPoolExecutor(max_workers=max(1, os.cpu_count()-1)) # TODO: REMOVE


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

        # create process output monitor
        self.process_output_monitor = ProcessOutputMonitor(self.tab_panel)

        ################################
        # add functionality and controls
        ################################
        self.add_tab_button.clicked.connect(self.add_tab)
        self.tab_panel.tabCloseRequested.connect(self.close_tab)
        self.run_all_jobs_button.clicked.connect(self.run_all_jobs)
        self.stop_all_jobs_button.clicked.connect(self.stop_all_jobs)

        self.process_output_monitor.update_output.connect(self.handle_process_output)
        self.process_output_monitor.monitor_outputs()

        self.show()


    #def handle_process_output(self, job_panel, txt):
    @pyqtSlot(JobPanel, str)
    def handle_process_output(self, job_panel, msg):
        job_panel.output_window.insertPlainText(msg)
        job_panel.output_window.moveCursor(QtGui.QTextCursor.End)



    def add_tab(self):
        """
        Adds a new tab to the JobTabPanel
        """
        active_tab_index = self.tab_panel.currentIndex()
        if active_tab_index >= 0:
            argparse_namespace = self.tab_panel.widget(active_tab_index).get_args()
        else:
            argparse_namespace = yt2mp3.parse_command_line_args()

        new_tab = JobPanel(self.worker_thread_pool, self.gui_communicator_thread_pool, argparse_namespace)
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
        self.worker_thread_pool.shutdown(wait=False)
        self.process_output_monitor.stop()
        event.accept()





