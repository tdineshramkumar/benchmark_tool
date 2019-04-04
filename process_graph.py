import psutil
import time
import json
import math
import sys
import os


def convert_daemon(out_file=None, err_file=None):
    """
        This function converts the calling process into a daemon,
        logs the standard output and standard error into log_file if any
     """
    sys.stdout.flush()
    sys.stderr.flush()
    os.close(sys.stdin.fileno())

    stdout = open(out_file, 'w') if out_file else open(os.devnull, 'w')
    stderr = open(err_file, 'w') if err_file else open(os.devnull, 'w')

    """ Log to the corresponding file """
    os.dup2(stdout.fileno(), sys.stdout.fileno())
    os.dup2(stderr.fileno(), sys.stderr.fileno())

    """ Become a session leader and decouple from parent environment """
    os.setsid()
    os.chdir("/")
    os.umask(0)


def monitor_process_branches_daemon(interval=0.1, out_file="branching_out.log", err_file="branching_error.log",
                                    monitor_file="monitor_processes.log"):
    """ This function creates a daemon process to monitor the current process and its children,
        Note: this process does not monitor itself
        this also monitors the system usage of processes
     """
    """ Get current process details before creating daemon process """
    root_pid_ = os.getpid()
    root_ppid_ = os.getppid()
    root_process_ = psutil.Process()
    daemon_pid_ = os.fork()
    """ Create the monitor file in the current user directory, before launching the daemon """
    monitor_file_ = open(monitor_file, 'w')
    """ Thus a function to write to monitor file """
    monitor = lambda *values, **kwargs: print(*values, file=monitor_file_, **kwargs)

    """ Fork and create a daemon process to monitor its parent process """
    if daemon_pid_ == 0:
        """ Monitor from a daemon process """
        daemon_pid_ = os.getpid()
        convert_daemon(out_file, err_file)
        error = lambda *values, **kwargs: print(*values, file=sys.stderr, **kwargs)
        """ Also open file for logging processes stats """

        running_processes_ = {root_process_}
        """ Also keep track of current process, to prevent processing it and waiting for itself """
        daemon_process_ = psutil.Process()
        """ Keep track or original parent id's as if parent dies """
        parent_pids_ = {root_pid_: root_ppid_}
        while running_processes_:
            """ Discover new processes by looking for children of existing processes """
            for process_ in running_processes_.copy():
                """ Loop using a copy as running_processes_ may get modified, 
                    as some process may throw exception on exit while requesting for its children 
                    (discovering new processes), discovering new process using 
                    children of original processes is required as if some process dies,
                    its children may be adopted and becoming unreachable, 
                    also not all processes can be monitored, 
                    if a process is forked and creates children and dies before being monitored, 
                    entire sub-tree is lost, thus it is suitable to monitor programs with child process
                    that are relatively long running enough to be processed, 
                    that is dies after some time after forking """
                try:
                    """ Don't go for recursive as it will be monitored and avoid un-necessary looping,
                     But however it will capture the new grand-children in this iteration itself """
                    for child_process_ in process_.children():
                        child_pid_ = child_process_.pid
                        child_ppid_ = process_.pid
                        """ Current process under consideration cannot be daemon itself """
                        if child_process_ not in running_processes_ and child_pid_ != daemon_pid_:
                            running_processes_.add(child_process_)
                            parent_pids_[child_pid_] = child_ppid_
                except psutil.Error:
                    """ If exception is thrown, then process may have exited """
                    running_processes_.remove(process_)
                    process_pid_ = process_.pid
                    process_ppid_ = parent_pids_[process_pid_]
                    process_creation_time_ = process_.create_time()
                    """ Note: exit time is an estimation, based on when exception is thrown """
                    process_exit_time_ = time.time()
                    print(json.dumps({
                        "pid": process_pid_,
                        "ppid": process_ppid_,
                        "creation_time": process_creation_time_,
                        "exit_time": process_exit_time_,
                        "life_time": process_exit_time_ - process_creation_time_,
                        "root": process_pid_ == root_pid_,
                    }), flush=True)

            """ Now the monitoring phase, after discovering the processes, re-run the above loop
                         instead of looking for children, now get system usages """
            for process_ in running_processes_.copy():
                try:
                    process_pid_ = process_.pid
                    process_ppid_ = parent_pids_[process_pid_]
                    stats = {
                        'pid': process_pid_, 'ppid': process_ppid_,
                        'cpu_times': {'user': process_.cpu_times().user, 'system': process_.cpu_times().system},
                        'memory': {'rss': process_.memory_info().rss, 'vms': process_.memory_info().vms},
                        'num_fds': process_.num_fds(), 'num_threads': process_.num_threads(),
                        'time': time.time(),
                    }
                    monitor(json.dumps(stats), flush=True)
                except psutil.Error:
                    """ If a process exits, then remove """
                    running_processes_.remove(process_)
                    process_pid_ = process_.pid
                    process_ppid_ = parent_pids_[process_pid_]
                    process_creation_time_ = process_.create_time()
                    """ Note: exit time is an estimation, based on when exception is thrown """
                    process_exit_time_ = time.time()
                    print(json.dumps({
                        "pid": process_pid_,
                        "ppid": process_ppid_,
                        "creation_time": process_creation_time_,
                        "exit_time": process_exit_time_,
                        "life_time": process_exit_time_ - process_creation_time_,
                        "root": process_pid_ == root_pid_,
                    }), flush=True)

            """ Wait for specified interval before re-discovering and monitoring  """
            time.sleep(interval)
        """ Close the monitor file before exiting daemon """
        monitor_file_.close()
        error("daemon process", daemon_pid_, "exited")
        exit(0)
    """ Close the monitor log file in the parent process """
    monitor_file_.close()
    print("daemon monitoring process running with pid", daemon_pid_)
    """ Return the pid of daemon if needed """
    return daemon_pid_


def __drawing_order__(all_stats_, pid_):
    """ Return the drawing order of the pid(s) """
    if not all_stats_[pid_]["sorted_children"]:
        """ If no children, then drawing only itself """
        return [pid_]
    """Else draw itself, then the draw order of the children, on after the other, 
    assuming children processes are sorted accordingly """
    order_ = [pid_]
    for child_pid_ in all_stats_[pid_]["sorted_children"]:
        order_ += __drawing_order__(all_stats_, child_pid_)
    return order_


def __find_num_descendants__(all_stats_, pid_):
    """ Assuming all_stats forms a tree """
    if not all_stats_[pid_]["children"]:
        """ if no children, then no descendants """
        all_stats_[pid_]["num_descendants"] = 0
    else:
        """ If some number of children, then number of descendants is sum of number of 
        descendants of children and number of children """
        all_stats_[pid_]["num_descendants"] = len(all_stats_[pid_]["children"])
        for child_pid_ in all_stats_[pid_]["children"]:
            """ Update the descendants count of children """
            __find_num_descendants__(all_stats_, child_pid_)
            """ Then, update current based on it """
            all_stats_[pid_]["num_descendants"] += all_stats_[child_pid_]["num_descendants"]


def generate_process_cpu_utilization_graph(monitor_file="monitor_processes.log", figure_file="monitor_cpu.png"):
    """ This function plots the CPU Utilization of all processes onto the same graph
    using the specified log file and outputs the result to specified file """
    processes_stats_ = {}
    with open(monitor_file) as file:
        for line in file:
            process_stats_ = json.loads(line)
            """ Later on update the cpu_percent """
            process_stats_["cpu_percent"] = 0.0
            process_pid_ = process_stats_["pid"]
            if process_pid_ not in processes_stats_:
                """ Add a empty list """
                processes_stats_[process_pid_] = []
            """ Append to stats of the given process """
            processes_stats_[process_pid_].append(process_stats_)

        """ Now find the CPU Utilization for each of the processes """
        for pid_ in processes_stats_:
            for i in range(1, len(processes_stats_[pid_])):
                """ Find the CPU Utilization using current and previous CPU times"""
                process_stats_cur_ = processes_stats_[pid_][i]
                process_stats_prv_ = processes_stats_[pid_][i - 1]
                user_time_spent = process_stats_cur_["cpu_times"]["user"] - process_stats_prv_["cpu_times"]["user"]
                sys_time_spent = process_stats_cur_["cpu_times"]["system"] - process_stats_prv_["cpu_times"]["system"]
                time_interval = process_stats_cur_["time"] - process_stats_prv_["time"]
                if time_interval != 0.0:
                    assert time_interval > 0
                    processes_stats_[pid_][i]["cpu_percent"] = (user_time_spent + sys_time_spent) / time_interval

        """ Find the starting time, minimum of all times across all process """
        start_time = min(processes_stats_[pid_][0]["time"] for pid_ in processes_stats_)
        import matplotlib.pyplot as plt
        """ Plot the CPU utilization of all processes using the matplotlib on the same plot """
        plt.figure(figsize=(20, 10))
        for pid_ in processes_stats_:
            times = [process_stats_["time"] - start_time for process_stats_ in processes_stats_[pid_]]
            cpu_percent = [process_stats_["cpu_percent"] for process_stats_ in processes_stats_[pid_]]
            plt.plot(times, cpu_percent, label=str(pid_))
        plt.xlabel("Time")
        plt.ylabel("CPU Utilization")
        plt.legend()
        plt.title("CPU Utilization of processes")
        plt.savefig(figure_file)
        plt.clf()


def generate_process_branching_image(out_log_file="branching_out.log", figure_file="branching.png", time_resolution=0.1,
                                     line_width=1, separation_width=5):
    """ This function reads the process life time logs and generates a phylogenetic tree sort of graph of processes
     based on parent process relations and process life times, time resolution line width and
      separation width are used to draw graphs """
    """
    Time resolution is used to control the x axis scale, that is, how much time each pixel along x-axis represent,
    Line width controls thickness of lines and separation_width controls spacing between lines.
    """
    assert time_resolution > 0
    all_stats_ = dict()
    with open(out_log_file) as file:
        for line in file:
            process_stats_ = json.loads(line)
            process_stats_["children"] = []
            all_stats_[process_stats_["pid"]] = process_stats_
    """ Get the overall starting time and completion time and total life time, useful for plotting """
    creation_time_ = min(all_stats_[pid__]["creation_time"] for pid__ in all_stats_)
    completion_time_ = max(all_stats_[pid__]["exit_time"] for pid__ in all_stats_)
    print("Creation time:", creation_time_, "Completion time:", completion_time_)
    life_time_ = completion_time_ - creation_time_
    """ There can be only one root process """
    root_processes_pid_ = list(filter(lambda pid__: all_stats_[pid__]["root"], all_stats_))
    assert len(root_processes_pid_) == 1
    root_process_pid_ = root_processes_pid_[0]

    """ Construct the process tree """
    for pid__ in all_stats_:
        ppid__ = all_stats_[pid__]["ppid"]
        if pid__ != root_process_pid_:
            all_stats_[ppid__]["children"].append(pid__)

    """ Update the number of descendants for a given process """
    __find_num_descendants__(all_stats_, root_process_pid_)
    """ Convert creation_times to relative creation times """
    for pid__ in all_stats_:
        all_stats_[pid__]["relative_creation_time"] = all_stats_[pid__]["creation_time"] - creation_time_
        all_stats_[pid__]["relative_exit_time"] = all_stats_[pid__]["exit_time"] - creation_time_
        all_stats_[pid__]["relative_creation_time_units"] = int(
            all_stats_[pid__]["relative_creation_time"] / time_resolution)
        all_stats_[pid__]["relative_exit_time_units"] = int(all_stats_[pid__]["relative_exit_time"] / time_resolution)

    """ Now order the processes based suitable for drawing the graph based on
     parent-child relation and creation time (fork time) """
    for pid__ in all_stats_:
        all_stats_[pid__]["sorted_children"] = sorted(all_stats_[pid__]["children"], reverse=True,
                                                      key=lambda __pid: all_stats_[__pid]["creation_time"])
    drawing_order_ = __drawing_order__(all_stats_, root_process_pid_)
    print("ORDER:", drawing_order_)

    """ Now draw the line graph """
    life_time_units_ = math.ceil(life_time_ / time_resolution) + separation_width * 2
    from PIL import Image, ImageDraw
    num_stats_ = len(all_stats_)
    image_width, image_height = life_time_units_, num_stats_ * line_width + (num_stats_ + 1) * separation_width
    image = Image.new("RGB", (image_width, image_height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    for index_, pid_ in enumerate(drawing_order_):
        """ Draw the time lines"""
        y_offset = line_width * index_ + separation_width * (index_ + 1)
        xy_ = (separation_width + all_stats_[pid_]["relative_creation_time_units"], y_offset) + \
              (separation_width + all_stats_[pid_]["relative_exit_time_units"], y_offset)
        draw.line(xy_, (0, 0, 0), width=line_width)
        """ Now connect them to their parents """
        if pid_ != root_process_pid_:
            x_offset = separation_width + all_stats_[pid_]["relative_creation_time_units"]
            parent_index_ = drawing_order_.index(all_stats_[pid_]["ppid"])
            y_parent_offset = line_width * parent_index_ + separation_width * (parent_index_ + 1)
            xy_ = (x_offset, y_offset) + (x_offset, y_parent_offset)
            draw.line(xy_, (0, 0, 0), width=line_width)

    print("Saving process branching image to", figure_file, "...")
    image.save(figure_file)
    for pid__ in all_stats_:
        print(all_stats_[pid__])


if __name__ == "__main__":
    """ Run the program with default arguments """
    generate_process_branching_image()
    generate_process_cpu_utilization_graph()

