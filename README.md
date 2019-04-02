### Automate Benchmark testing using python script
#### monitor.py
This script is used to automate benchmark runs, with single process client and server.
This script launch server and after some delay the client. And terminates the server 
once the client terminates. 
Also it launches monitoring programs to monitor client and server system usage like 
CPU and Memory using _psutil_ package.
Also it supports logging client and server standard output and error logs to separate 
log files.

System usages of client and server are logged to files with postfix _-monitor-client.log_ 
and _-monitor-server.log_  respectively.
  
**NOTE**: _It handles only single process client and server_

**Usage**:  python3 monitor.py --scenario "some benchmark name" --client "the client command"
--server "the server command" [ --log ] 

Example: python3 monitor.py --scenario dummy_test --client "./client" --server "./server" 
--log

#### plot.py

This script is used to plot the system metrics obtained from the monitor.py script.
This script plots the server and client metrics side by side on the same plot.

**Usage**:  python3 plot.py --scenario "the scenario to plot"

Example: python3 plot.py --scenario dummy_test