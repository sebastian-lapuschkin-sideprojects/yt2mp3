from PyQt5.QtCore import QObject             # pylint: disable=F0401
from PyQt5.QtCore import pyqtSignal
from .job_panel import JobPanel

from threading import current_thread
from threading import Thread

import time

class ProcessOutputMonitor(QObject):
    """
    A Monitor for handling subprocess communication
    """
    update_output = pyqtSignal(JobPanel, str)  # the signal
    #update_output = pyqtSignal(str)  # the signal
    #update_output = pyqtSignal(str)
    #update_output = pyqtSignal()

    def __init__(self, tab_panel):
        super(QObject, self).__init__()
        self.tabs = tab_panel
        self.monitor = None
        self.stopped = False

    def monitor_outputs(self):
        self.monitor = Thread(target=self._monitor_outputs) #, parent=self)
        self.monitor.deamon = True
        self.monitor.setName('Process Output Monitor Thread')
        self.monitor.start()

    def stop(self):
        self.stopped = True

    def _monitor_outputs(self):
        print('MONITOR RUNNING!')
        # DUMMY FUNCTIONALITY. REPLACE WITH READING FROM jobPanel child process pipes
        while not self.stopped:
            for i in range(len(self.tabs)):
                try:
                    job_panel = self.tabs.widget(i)
                    msg = job_panel.get_process_output(timeout=0.1) #NO TIMEOUT NEEDED. NOTE .
                    if msg:
                        self.update_output.emit(job_panel, msg)
                except Exception as e:
                    print(e)
            time.sleep(0.005)
        print('MONITOR STOPPED!')