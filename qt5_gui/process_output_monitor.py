from PyQt5.QtCore import QObject             # pylint: disable=F0401
from PyQt5.QtCore import pyqtSignal
from .job_panel import JobPanel

from threading import current_thread
from threading import Thread

import os
import time

class ProcessOutputMonitor(QObject):
    """
    A Monitor for handling subprocess communication
    """
    update_output = pyqtSignal(JobPanel, str)   # the text output signals
    update_stati = pyqtSignal(dict)
    update_tabinfo = pyqtSignal(dict)      # process tab names

    def __init__(self, tab_panel):
        super(QObject, self).__init__()
        self.tabs = tab_panel
        self.monitor = None
        self.stopped = False

    def monitor_outputs(self):
        self.monitor = Thread(target=self._monitor_job_panels) #, parent=self)
        self.monitor.deamon = True
        self.monitor.setName('Process Output Monitor Thread')
        self.monitor.start()

    def stop(self):
        self.stopped = True

    def _monitor_job_panels(self):
        print('MONITOR RUNNING!')
        # DUMMY FUNCTIONALITY. REPLACE WITH READING FROM jobPanel child process pipes
        while not self.stopped:
            job_status_summary = {   JobPanel.STATUS_IDLE:0,
                            JobPanel.STATUS_SUBMITTED:0,
                            JobPanel.STATUS_RUNNING:0,
                            JobPanel.STATUS_STOPPED:0,
                            JobPanel.STATUS_FINISHED:0
                        }
            tab_information = {} #job status and tab name
            for i in range(len(self.tabs)):
                try:
                    job_panel = self.tabs.widget(i)
                    job_status_summary[job_panel.job_status] += 1
                    tab_information[i] = (job_panel.job_status, os.path.basename(job_panel.output_location_input.text()))
                    msg = job_panel.get_process_output(timeout=0.1) #NO TIMEOUT NEEDED. NOTE .
                    if msg:
                        self.update_output.emit(job_panel, msg)
                except Exception as e:
                    print(e)
            self.update_stati.emit(job_status_summary)
            self.update_tabinfo.emit(tab_information)
            time.sleep(1/20)
        print('MONITOR STOPPED!')