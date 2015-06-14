import sys
from time import sleep
from daemon import runner
import os
import glob
import logging

# custom packages
from .controller import Controller
from .conf import options


class Churada:
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path = '/var/run/churada/churada.pid'
        self.pidfile_timeout = 1
    def run(self):
        self.logger = logging.getLogger("Churada")
        controller = Controller(**options['controller_args'])
        while True:
            controller.act()
            sleep(options['period'])

logging.basicConfig(filename=options['logfile'],level=options['loglevel'])
app = churada()
daemon_runner = runner.DaemonRunner(app)
# if we're just exiting, just stop the daemon and exit
daemon_runner.do_action()
