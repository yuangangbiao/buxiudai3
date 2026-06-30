import sys, os
print("Python version:", sys.version)
print("CWD:", os.getcwd())
print("Can write to CWD:", os.access(os.getcwd(), os.W_OK))
with open("simple_test_output.txt", "w") as f:
    f.write("OK")
print("Write test done")
