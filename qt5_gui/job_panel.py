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

import yt2mp3
import yt2mp3_utils

from threading import current_thread
from threading import Thread
import argparse
import os

class JobPanel(QWidget):
    """
    A Widget class representing all information required for executing
    a download+conversion job
    """

    #JOB STATI
    STATUS_IDLE = 0
    STATUS_SUBMITTED = 1
    STATUS_RUNNING = 2
    STATUS_FINISHED = 3
    STATUS_STOPPED = 4
    STATUS_FAILED = 5

    def __init__(self, worker_thread_pool, gui_communicator_thread_pool, argparse_namespace):
        """
        Constitutes a GUI container for job information and execution.
        Holds the necessary data, allows editing of parameters.

        Parameters:
        -----------
        worker_thread_pool: multiprocessing.Pool - Executor for running jobs.
        gui_communicator_thread_pool: multiprocessing.Pool - Executor for communicating with background processes

        argparse_namespace: argparse.Namespace - container for job data
        """
        super(QWidget, self).__init__()

        # use this ThreadPoolExecutor instance for executing jobs
        self.worker_thread_pool = worker_thread_pool
        self.communicator_thread_pool = gui_communicator_thread_pool
        # use this argparse.Namespace instance for job data specification
        self.argparse_namespace = argparse_namespace
        # use this to keep track of all created subprocess (in case they need killin')
        # yt2mp3.download_convert_split provides an interface for that list.
        self.child_processes = []
        self.worker_thread = None
        self.communicator_thread = None
        self.containing_tab = None
        self.job_status = JobPanel.STATUS_IDLE


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
        self.output_window.setEnabled(True) # start with "false"
        self.output_window.setReadOnly(True)

        self.run_job_button = QPushButton('Run')
        self.stop_job_button = QPushButton('Stop')
        self.job_status_label = QLabel('')

        ##############
        # assemble tab
        ##############
        layout = QGridLayout()

        layout.addWidget(self.video_id_url_label, 0, 0)
        layout.addWidget(self.video_id_url_input, 0, 1)

        layout.addWidget(self.output_location_label, 1, 0)
        layout.addWidget(self.output_location_input, 1, 1)
        layout.addWidget(self.output_location_dialog_button, 1, 2)

        layout.setRowStretch(2,1)  # allows the construction of "empty lines"

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
        layout.addWidget(self.job_status_label, 7, 2)
        layout.addWidget(self.output_window, 8, 0, 1, 3)
        layout.setRowStretch(8, 2)  # make output text box two rows high

        self.setLayout(layout)      # install GUI elements

        ################################
        # add functionality and controls
        ################################
        self.run_job_button.clicked.connect(self.run_job_callback_fxn)
        self.stop_job_button.clicked.connect(self.stop_job_callback_fxn)

        self.video_id_url_input.textChanged.connect(self.parse_video_id_url_callback_fxn)
        self.output_location_input.textChanged.connect(self.parse_output_location_callback_fxn)

        self.segment_output_checkbox.toggled.connect(self.segment_output_state_changed_callback_fxn)
        self.output_segment_duration_input.textChanged.connect(self.parse_output_segment_length_callback_fxn)
        self.output_segment_name_pattern_input.textChanged.connect(self.parse_output_name_pattern_callback_fxn)

        self.output_location_dialog_button.clicked.connect(self.select_output_location_from_qfiledialog_callback_fxn)

        # configure UI activity status
        self.update_user_interface()

    def is_runnable(self):
        """
        Are all required arguments present to run the job?
        """

        if self.job_status in [JobPanel.STATUS_SUBMITTED, JobPanel.STATUS_RUNNING]:
            # currently submitted stuff can not be re-submitted
            return False
        elif not ((self.argparse_namespace.video and len(self.argparse_namespace.video[0]) > 0) and self.argparse_namespace.output):
            # can not run incomplete input sets
            return False
        elif self.segment_output_checkbox.isChecked() and not (self.argparse_namespace.segment_name and self.argparse_namespace.segment_length and self.argparse_namespace.segment_length > 0):
            # can not run incomplete optional input sets
            return False
        elif self.job_status in [JobPanel.STATUS_FINISHED]:
            # no running of finished jobs to avoid overwriting of results.
            return False
        else:
            return True

    def is_stoppable(self):
        """
        Is there anything in this job, which can be stopped?
        """
        return self.job_status in [JobPanel.STATUS_RUNNING, JobPanel.STATUS_SUBMITTED]

    def enable_these_elements(self, *args):
        for a in args:
            a.setEnabled(True)

    def disable_these_elements(self, *args):
        for a in args:
            a.setEnabled(False)

    def gui_to_edit_mode(self):
        """
        enable/disabled gui elements corresponding to a passive state of the job
        """
        self.enable_these_elements(self.video_id_url_input,
                                   self.output_location_input,
                                   self.output_location_dialog_button,
                                   self.segment_output_checkbox)
        if self.segment_output_checkbox.isChecked():
            self.enable_these_elements(self.output_segment_name_pattern_input,
                                       self.output_segment_duration_input)
        self.disable_these_elements(self.stop_job_button,
                                    self.output_window)

        if self.is_runnable():
            self.enable_these_elements(self.run_job_button)
        else:
            self.disable_these_elements(self.run_job_button)

    def gui_to_submitted_mode(self):
        """
        enable/disable gui elements corresponding to an active state of the job
        """
        self.enable_these_elements( self.output_window,
                                    self.stop_job_button)
        self.disable_these_elements(self.run_job_button,
                                    self.video_id_url_input,
                                    self.output_location_input,
                                    self.output_location_dialog_button,
                                    self.segment_output_checkbox,
                                    self.output_segment_duration_input,
                                    self.output_segment_name_pattern_input)


    def update_user_interface(self):
        """
        Enables/disables UI elements wrt process status and/or enterd data.
        """
        if self.job_status == JobPanel.STATUS_IDLE:
            self.job_status_label.setText('Status: Idle')
            self.gui_to_edit_mode()

        elif self.job_status == JobPanel.STATUS_SUBMITTED:
            self.job_status_label.setText('Status: Submitted')
            self.gui_to_submitted_mode()

        elif self.job_status == JobPanel.STATUS_RUNNING:
            self.job_status_label.setText('Status: Running')
            # comes after running. no change in UI elements

        elif self.job_status == JobPanel.STATUS_FINISHED:
            self.job_status_label.setText('Status: Finished')
            # keep inputs deactivated. all of them.
            self.disable_these_elements(self.stop_job_button)

        elif self.job_status == JobPanel.STATUS_STOPPED:
            self.job_status_label.setText('Status: Stopped')
            self.gui_to_edit_mode()
            # reactivate inputs to allow editing/fixing of wrong params

        elif self.job_status == JobPanel.STATUS_FAILED:
            self.job_status_label.setText('Status: Failed')
            self.gui_to_edit_mode()
            # reactivate inputs to allow editing/fixing of wrong params

        else:
            raise Exception('Unknown job status id {}'.format(self.job_status))
        #TODO Capture REGULAR printline outputs! (reroute to process_watcher.pipes?)
        #TODO add job cleanup button to kill remaining .tmp-folders.


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
            arg_copy = argparse.Namespace(**vars(self.argparse_namespace))
            arg_copy.video = []
            arg_copy.video.extend(self.argparse_namespace.video)
            return arg_copy
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

        # update UI elements
        self.update_user_interface()

    def parse_output_location_callback_fxn(self):
        """
        Attempts to parse output path
        """
        self.argparse_namespace.output = self.output_location_input.text()
        # update UI elements
        self.update_user_interface()

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
                self.argparse_namespace.segment_length = -1
                pass
        else:
            self.argparse_namespace.segment_length = None
        # update UI elements
        self.update_user_interface()


    def parse_output_name_pattern_callback_fxn(self):
        """
        Attempts to parse the output name pattern for segmented mp3 files
        """
        self.argparse_namespace.segment_name = self.output_segment_name_pattern_input.text()
        # update UI elements
        self.update_user_interface()

    def run_job_function(self):
        """
        Container function for submission to self.thread_pool
        holding all necessary functionality for runnanle and stoppable job treads
        """
        if self.thread_level_job_stop_check(): return

        self.job_status = JobPanel.STATUS_RUNNING
        self.update_user_interface()
        self.worker_thread = current_thread()

        try:
            print(self.argparse_namespace) # TODO: removes
            yt2mp3_utils.check_requirements()
            yt2mp3.download_convert_split(self.argparse_namespace, self)
            if not self.job_status == JobPanel.STATUS_STOPPED:
                self.job_status = JobPanel.STATUS_FINISHED

        except Exception as e:
            # has the job been stopped manually, or has it crashed?
            if not self.job_status == JobPanel.STATUS_STOPPED:
                self.job_status = JobPanel.STATUS_FAILED
                print(e)

        # update UI elements
        self.update_user_interface()

    def update_process_output(self):
        self.communicator_thread = current_thread()
        while self.job_status in [JobPanel.STATUS_SUBMITTED, JobPanel.STATUS_RUNNING]:
            #self.output_window.setPlainText('self.job_status = {} in {} from {}'.format(self.job_status, self.worker_thread, self.communicator_thread))
            print('self.job_status = {} in {} from {}'.format(self.job_status, self.worker_thread, self.communicator_thread))
            time.sleep(0.1)
        print('FINAL JOB STATUS: {}'.format(self.job_status))

    def run_job_callback_fxn(self):
        """
        Try to run this JobPanel's job according to parameterization
        """
        self.job_status = JobPanel.STATUS_SUBMITTED
        self.update_user_interface()
        self.worker_thread_pool.submit(self.run_job_function)
        # self.communicator_thread_pool.submit(self.update_process_output)

        # update UI elements


    def thread_level_job_stop_check(self):
        if self.job_status == JobPanel.STATUS_STOPPED:
            self.update_user_interface()
            return True
        else:
            return False

    def stop_job_callback_fxn(self):
        """
        Try to stop this JobPanel's job according to parameterization
        """
        self.job_status = JobPanel.STATUS_STOPPED

        for p in self.child_processes:
            print('KILLING CHILD PROCESS', p)
            p.kill()

        self.child_processes = []
        self.worker_thread = None
        self.communicator_thread = None
        # update UI elements
        self.update_user_interface()

    def get_process_output(self, timeout):
        """
        Collects and returns the string produced by all subprocesses
        """

        # problem: youtube-dl writes to stdout, ffmpeg writes to stderr.
        # attempting to read the one blocks the other.
        msg = ''
        for p in self.child_processes:
            out_line = p.stdout.readline()
            if out_line:
                return out_line
                #msg += out_line

                # PROBLEM: FFMPEG WRITES IN x-sec intervals. blocks all other stdouts with only one thread managing console IO
                # seprate manager for all processes?
                # NOTE: maybe later. for now, this is ok.

        #return msg
