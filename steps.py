import process_graph
import os
import time

""" Call this method to start monitoring the process branching """
process_graph.monitor_process_branches_daemon(interval=0.1)


""" Application code, which forks, and we want to monitor 
forking pattern of the program/process """

num_steps = 10
for i in range(num_steps):
    time.sleep(1)
    pid = os.fork()
    if pid == 0:
        continue
    break

""" Spend some time after forking for monitoring process to be 
able to scan through its child processes """
time.sleep(2)
