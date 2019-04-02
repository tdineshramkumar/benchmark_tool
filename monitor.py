"""
    This is main program to run the benchmarks, it is limited to clients and server with single process applications.
    This script enables to automate benchmark tests with single process clients and servers.
    This script monitors the CPU, Memory and some other system parameters using psutil library of the client and
    server application.
    WORKING:
        This script launches server on a separate process, and a monitoring process to log its system usage.
        This script launches client on a separate process after specified delay, and a monitoring process
        When client completes execution, determined by the monitoring process, client monitoring process terminates the
        server by sending a kill signal.
        The script terminates when server terminates.

    This script supports logging of client and server outputs and errors to separate log files. (use --log option)
"""

import os
from bench import create_daemon_and_monitor
from bench import execute_command
import argparse
import signal

parser = argparse.ArgumentParser()
parser.add_argument('--scenario', '-S', help='specify the benchmark scenario, '
                                             'it is just used to construct file names for logs of client and server',
                    required=True)
parser.add_argument('--server', '-s', help='the server command to execute', required=True)
parser.add_argument('--client', '-c', help='the client command to execute', required=True)
parser.add_argument('--log', '-l',  help="whether to log server and command outputs to file", action="store_true")
parser.add_argument('--wait', '-w', help='time to wait before executing client after starting server',
                    type=int, default=5)
parser.add_argument('--idle', '-i', help='time to wait before executing command, '
                                         'the time to wait for monitoring process to start up',
                    type=int, default=1)
args = parser.parse_args()

parent_pid = os.getpid()
server_pid = os.fork()

if server_pid == 0:
    # In case of server
    server_pid = os.getpid()

    client_pid = os.fork()
    if client_pid == 0:
        # In case of client
        client_pid = os.getpid()
        # wait for some time for server to boot up
        # then, execute the client task,
        # then also monitor script
        # on exit send kill signal to server process
        kill_server = lambda: os.kill(server_pid, signal.SIGKILL)
        client_log_file = args.scenario + '-monitor-client.log'
        create_daemon_and_monitor(client_pid, log_file=client_log_file, on_complete_handler=kill_server)
        client_output_log_file = args.scenario + '-output-client.log' if args.log else None
        client_error_log_file = args.scenario + '-error-client.log' if args.log else None
        execute_command(args.client, args.idle + args.wait, out_log_file=client_output_log_file,
                        err_log_file=client_error_log_file)

    # The server process, continues
    # execute the server task,
    # then when monitor process exits as server exits,
    # it may signal the server
    server_log_file = args.scenario + '-monitor-server.log'
    create_daemon_and_monitor(server_pid, log_file=server_log_file)
    server_output_log_file = args.scenario + '-output-server.log' if args.log else None
    server_error_log_file = args.scenario + '-error-server.log' if args.log else None
    execute_command(args.server, args.idle, out_log_file=server_output_log_file, err_log_file=server_error_log_file)


# Main process
print("Running the benchmark")
print("Waiting for server to exit ...")
_, status = os.waitpid(server_pid, 0)
print("Server process exited with ", status)
