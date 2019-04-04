"""
    This file contains utility methods to monitor process usage, create daemon process and to execute command.
    This benchmark tool can only be used to monitor single process clients and servers.
"""

import os
import sys
import json
import time
import psutil
import shlex


def daemon_process(log_file=None):
    """
        This function converts the calling process into a daemon,
        logs the standard output and standard error into log_file if any
     """
    sys.stdout.flush()
    sys.stderr.flush()
    os.close(sys.stdin.fileno())
    if log_file:
        f = open(log_file, 'w')
    else:
        f = open(os.devnull, 'w')
    """ Log to the corresponding file """
    os.dup2(f.fileno(), sys.stdout.fileno())
    os.dup2(f.fileno(), sys.stderr.fileno())
    """ Become a session leader and decouple from parent environment """
    os.setsid()
    os.chdir("/")
    """ What does it do ? """
    os.umask(0)


def monitor_process_stats(pid, interval=1):
    """ Print stats of the process in json format """
    """ Print some info about the system like # cpu cores and memory """
    print('MEMORY:', psutil.virtual_memory().total, 'bytes', '\t', 'CPU:', psutil.cpu_count(logical=True), 'VIRT',
          psutil.cpu_count(logical=False), 'PHY', psutil.cpu_freq().current, 'MHz', flush=True)
    try:
        process = psutil.Process(pid=pid)
        """ Print some info about process like pid, path, creation time, user"""
        print('PID:', process.pid, 'PPID:', process.ppid(), 'USER:', process.username(),
              'EXE:', process.exe(), 'CREATION:', process.create_time(), flush=True)
        while True:
            """ Note: call to cpu_percent is blocking for the given interval """
            stats = {
                # CPU Stats
                'cpu_times': {
                    'user': process.cpu_times().user,
                    'system': process.cpu_times().system,
                },
                'cpu_percent': process.cpu_percent(interval=interval),

                # Memory Stats
                'memory': {
                    'rss': process.memory_info().rss,
                    'vms': process.memory_info().vms,
                },

                # Other Stats
                'num_fds': process.num_fds(),
                'num_threads': process.num_threads(),
                'time': time.time(),

            }
            print(json.dumps(stats), flush=True)
    except psutil.Error:
        pass
    finally:
        os.close(sys.stdout.fileno())
        os.close(sys.stderr.fileno())


def execute_command(command, wait=0, out_log_file=None, err_log_file=None):
    """ Wait for some time and then execute the command """
    print("waiting for ", wait, 'seconds before executing command', command)
    time.sleep(wait)
    """ Can't read from standard input """
    print("executing command", command)
    os.close(sys.stdin.fileno())

    """ If some log file is specified, then command output to that file """
    """ Flush out any existing buffer """
    """ Duplicate the opened log file's file descriptors to stdout and stderr  """
    if out_log_file:
        sys.stdout.flush()
        f = open(out_log_file, 'w')
        os.dup2(f.fileno(), sys.stdout.fileno())

    if err_log_file:
        sys.stderr.flush()
        f = open(err_log_file, 'w')
        os.dup2(f.fileno(), sys.stderr.fileno())

    cmd = shlex.split(command)
    os.execvp(cmd[0], cmd)


def create_daemon_and_monitor(pid, interval=1, log_file=None, on_complete_handler=None):
    """ This function creates a daemon process after forking and monitors the given pid,
        after termination of process which it monitors, it call the complete handler if any
     """
    daemon_pid = os.fork()
    if daemon_pid == 0:
        """ Child process becomes the daemon """
        daemon_process(log_file)
        monitor_process_stats(pid, interval)
        if on_complete_handler:
            """ Note: any logging in this handler will go to the
             log file given to the daemon"""
            on_complete_handler()
    return daemon_pid



