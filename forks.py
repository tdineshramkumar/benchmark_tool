import os
import time
import process_graph

""" Call this method to start monitoring the process branching """
process_graph.monitor_process_branches_daemon(interval=0.01)

""" Some application with some branching pattern """
time.sleep(0.2)

os.fork()
time.sleep(0.3)

os.fork()
time.sleep(0.4)

os.fork()
time.sleep(0.5)

os.fork()
time.sleep(0.6)

os.fork()
time.sleep(0.7)

os.fork()
time.sleep(0.8)

print("Process with PID ", os.getpid(), "exited after execution")
