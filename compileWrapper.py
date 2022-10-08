if __name__ == "__main__":
    import pexpect
    import os
    import glob
    import sys

    os.environ["TERM"] = "dumb"

    pOpenArgs = ["g++", "-w", "-c"] + sys.argv[1:]
    pOpenArgs.pop(3)
    (compile_output, exitstatus) = pexpect.run(" ".join(pOpenArgs), withexitstatus=1)
    if compile_output.decode("utf-8") != "":
        print(compile_output.decode("utf-8"))
        sys.exit(0)

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
            sys.exit(0)

    print("No error")
    sys.exit(0)