if __name__ == "__main__":
    import os
    import sys
    import pexpect
    import time

    import signal
    from contextlib import contextmanager

    from subprocess import Popen, PIPE
    from multiprocessing import Process

    class GracefulExit(Exception):
        pass

    def signal_handler(signum, frame):
        raise GracefulExit()

    def run():
        @contextmanager
        def timeout(time):
            # Register a function to raise a TimeoutError on the signal.
            signal.signal(signal.SIGALRM, raise_timeout)
            # Schedule the signal to be sent after ``time``.
            signal.alarm(time)

            try:
                yield
            except TimeoutError:
                print("+++++ exit code <5> +++++")
                pass
            finally:
                # Unregister the signal so it won't be triggered
                # if the timeout is not reached.
                signal.signal(signal.SIGALRM, signal.SIG_IGN)


        def raise_timeout(signum, frame):
            raise TimeoutError

        os.environ["TERM"] = "dumb"
        
        if os.path.isfile("main"):
            try:
                with timeout(900):
                    # False if non-interactive to not show the inputs of the user in the final
                    # output
                    echo = True if sys.argv[1] == "interactive" else False
                    child = pexpect.spawn("./main", encoding="utf-8", echo=echo)
                    print(child.pid) # This is needed to get the pid
                    child.interact()
                    child.expect(pexpect.EOF)
                    print(child.before)
                    time.sleep(0.1)
                    sys.stdout.flush()
                    child.close()
                    print("+++++ exit code <%d> +++++" % child.exitstatus)
            except Exception as e:
                print("+++++ exit code <6> +++++ %s" % e)
                
    def watcher(): 
        file_logs = []
        files = sys.argv[2:]
        
        generatedFiles = ["main"]
        for file in files:
            fs = file.split('.')
            if(fs[-1] == 'cpp'):
                # Exclude .o files
                generatedFiles.append("%s.o" % fs[0])
            elif(fs[-1] == 'h'):
                # Exclude .gch files
                generatedFiles.append("%s.gch" % file)
        
        files.extend(generatedFiles)

        excludePattern = "(%s)" % "|".join([p for p in files])
        pid = -1
        try:
            process = Popen(
                "inotifywait -qrme modify,attrib,move,create,delete,access --exclude '%s' ." % excludePattern,
                stdout=PIPE,
                shell=True,
                bufsize=1,
                universal_newlines=True,
            )

            pid = process.pid

            while True:
                nextline = process.stdout.readline()
                if nextline == "" and process.poll() is not None:
                    break

                file_logs.append(nextline.strip())
                sys.stdout.flush()

        except GracefulExit:
            # Modify file logs
            cleaned_file_logs = []

            EVENTS = {
                "CREATE_DIR": "CREATE,ISDIR",
                "CREATE_FILE": "CREATE",
                "WRITE_FILE": "MODIFY",
                "RENAME_ORIGINAL_FILE": "MOVED_FROM",
                "RENAME_FILE": "MOVED_TO",
                "RENAME_ORIGINAL_DIR": "MOVED_FROM,ISDIR",
                "RENAME_DIR": "MOVED_TO,ISDIR",
                "DELETE_FILE": "DELETE",
                "DELETE_DIR": "DELETE,ISDIR",
                "ACCESS_DIR": "ACCESS,ISDIR",
                "READ_FILE": "ACCESS"
            }

            temp_file_name = ""
            temp_folder_name = ""

            for file_log in file_logs:
                log_contents = file_log.split(" ")
                cwd = log_contents[0]
                event = log_contents[1]

                if event == EVENTS["ACCESS_DIR"]: continue

                name = cwd + log_contents[2]

                if event == EVENTS["CREATE_DIR"]:
                    cleaned_file_logs.append(
                        {
                            "file_name": name,
                            "is_folder": 1,
                            "operation": "create",
                        }
                    )
                elif event == EVENTS["CREATE_FILE"]:
                    cleaned_file_logs.append(
                        {
                            "file_name": name,
                            "is_folder": 0,
                            "operation": "create",
                        }
                    )
                elif event == EVENTS["WRITE_FILE"]:
                    # Check if file has been created. If not, then add create file log first
                    if not next((log for log in cleaned_file_logs if log["file_name"] == name and log["operation"] == "create"), None):
                        cleaned_file_logs.append({
                            "file_name": name,
                            "is_folder": 0,
                            "operation": "create"
                        })


                    cleaned_file_logs.append(
                        {
                            "file_name": name,
                            "is_folder": 0,
                            "operation": "write",
                        }
                    )

                elif event == EVENTS["RENAME_ORIGINAL_FILE"]:
                    temp_file_name = name
                elif event == EVENTS["RENAME_FILE"]:
                    cleaned_file_logs.append(
                        {
                            "file_name": temp_file_name,
                            "new_file_name": name,
                            "is_folder": 0,
                            "operation": "rename",
                        }
                    )
                    temp_file_name = ""
                elif event == EVENTS["RENAME_ORIGINAL_DIR"]:
                    temp_folder_name = name
                elif event == EVENTS["RENAME_DIR"]:
                    cleaned_file_logs.append(
                        {
                            "file_name": temp_folder_name,
                            "new_file_name": name,
                            "is_folder": 1,
                            "operation": "rename",
                        }
                    )
                    temp_folder_name = ""
                elif event == EVENTS["DELETE_FILE"]:             
                    cleaned_file_logs.append(
                        {
                            "file_name": name,
                            "is_folder": 0,
                            "operation": "delete"
                        }
                    )
                elif event == EVENTS["DELETE_DIR"]:
                    cleaned_file_logs.append(
                        {
                            "file_name": name,
                            "is_folder": 1,
                            "operation": "delete"
                        }
                    )
                elif event == EVENTS["READ_FILE"]:
                    cleaned_file_logs.append(
                        {
                            "file_name": name,
                            "is_folder": 0,
                            "operation": "read"
                        }
                    )

            print("<<<CODECHUMFILELOGSCODECHUM>>>", cleaned_file_logs)
            return pid

    signal.signal(signal.SIGTERM, signal_handler)


    watcher_process = Process(target=watcher)
    watcher_process.start()

    time.sleep(0.5)
    run_process = Process(target=run)
    run_process.start()
    run_process.join()

    watcher_process.terminate()
    sys.exit(0)     