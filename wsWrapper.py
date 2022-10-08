if __name__ == "__main__":
    import os
    import sys
    import glob
    import pexpect
    import time

    import signal
    from contextlib import contextmanager

    from subprocess import Popen, PIPE
    from multiprocessing import Process
    import json

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
                print("\n\n>>> Time Exceeded")
                pass
            finally:
                # Unregister the signal so it won't be triggered
                # if the timeout is not reached.
                s{"file_log" : ' + json.dumps(file_log) + '}ignal.signal(signal.SIGALRM, signal.SIG_IGN)

        def raise_timeout(signum, frame):
            raise TimeoutError

        pOpenArgs = ["g++", "-c"] + sys.argv[1:]
        pOpenArgs.pop(2)
        hasWarning = False
        (compile_output, exitstatus) = pexpect.run(" ".join(pOpenArgs), withexitstatus=1)
        if compile_output.decode("utf-8") != "":
            print(compile_output.decode("utf-8"))
            hasWarning = True

        if os.path.isfile("main.o"):
            object_linking_args = ["g++"]
            object_linking_args.extend(glob.glob("*.o"))
            object_linking_args.append("-o")
            object_linking_args.append("main")
            object_linking_args.append("-lm")
            (compile_output, exitstatus) = pexpect.run(
                " ".join(object_linking_args), withexitstatus=1
            )
            if exitstatus != 0:
                print(compile_output.decode("utf-8"))
                hasWarning = True

        if os.path.isfile("main"):
            try:
                with timeout(900):
                    child = pexpect.spawn("./main", encoding="utf-8", echo=False)
                    if not hasWarning:
                        print("ready<br>", end="")
                    child.interact()
                    child.expect(pexpect.EOF)
                    print(child.before)
                    time.sleep(0.1)
                    sys.stdout.flush()
                    child.close()
            except:
                pass

        print("\n\n>>> Program Terminated")
    
    def watcher():
        pid = -1

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
        try:
            process = Popen(
                "inotifywait -qrme modify,attrib,move,create,delete,access --exclude '%s' ." % excludePattern,
                stdout=PIPE,
                shell=True,
                bufsize=1,
                universal_newlines=True,
            )

            pid = process.pid

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

            def print_file_log(file_log):
                print('', end="")

            def determine_file_log(file_log):
                log_contents = file_log.split(" ")
                cwd = log_contents[0]
                event = log_contents[1]

                if event == EVENTS["ACCESS_DIR"]: return

                name = cwd + log_contents[2]

                final_file_log = None

                if event == EVENTS["CREATE_DIR"]:
                    final_file_log = {
                            "file_name": name,
                            "is_folder": 1,
                            "operation": "create",
                        }
                    
                elif event == EVENTS["CREATE_FILE"]:
                    final_file_log = {
                            "file_name": name,
                            "is_folder": 0,
                            "operation": "create",
                        }
                elif event == EVENTS["WRITE_FILE"]:
                    # Check if file has been created. If not, then add create file log first
                    # if not next((log for log in cleaned_file_logs if log["file_name"] == name and log["operation"] == "create"), None):
                    #     print({
                    #         "file_name": name,
                    #         "is_folder": 0,
                    #         "operation": "create"
                    #     })


                    final_file_log = {
                            "file_name": name,
                            "is_folder": 0,
                            "operation": "write",
                        }
                    

                elif event == EVENTS["RENAME_ORIGINAL_FILE"]:
                    final_file_log = {
                        "operation": "RENAME_ORIGINAL_FILE",
                        "file_name": name
                    }
                    # temp_file_name = name
                elif event == EVENTS["RENAME_FILE"]:
                    final_file_log = {
                            "file_name": "temp_file_name",
                            "new_file_name": name,
                            "is_folder": 0,
                            "operation": "rename",
                        }
                elif event == EVENTS["RENAME_ORIGINAL_DIR"]:
                    final_file_log = {
                        "operation": "RENAME_ORIGINAL_DIR",
                        "file_name": name
                    }
                elif event == EVENTS["RENAME_DIR"]:
                    final_file_log = {
                            "file_name": "",
                            "new_file_name": name,
                            "is_folder": 1,
                            "operation": "rename",
                        }
                    temp_folder_name = ""
                elif event == EVENTS["DELETE_FILE"]:             
                    final_file_log = {
                            "file_name": name,
                            "is_folder": 0,
                            "operation": "delete"
                        }
                elif event == EVENTS["DELETE_DIR"]:
                    final_file_log = {
                            "file_name": name,
                            "is_folder": 1,
                            "operation": "delete"
                        }
                elif event == EVENTS["READ_FILE"]:
                    final_file_log = {
                            "file_name": name,
                            "is_folder": 0,
                            "operation": "read"
                        }

                return final_file_log

            
            temp_file_name = ""
            while True:
                nextline = process.stdout.readline()
                if nextline == "" and process.poll() is not None:
                    break
                    
                file_log = determine_file_log(nextline.strip())
                if not file_log: continue
                if file_log['operation'] in ["RENAME_ORIGINAL_FILE", "RENAME_ORIGINAL_DIR"]:
                    temp_file_name = file_log['file_name']
                else:
                    if file_log['operation'] == "rename":
                        file_log["file_name"] = temp_file_name
                    print_file_log(file_log)
                
                sys.stdout.flush()

        except GracefulExit:
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