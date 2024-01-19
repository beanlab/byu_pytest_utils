import os
import subprocess

proc = subprocess.Popen(['python3', '-c', '[print(input("thing: ")) for _ in range(5)]'], 
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
os.set_blocking(proc.stdout.fileno(), False)

for _ in range(5):
    proc.stdin.write(b'cat\n')
    proc.stdin.flush()

    print(proc.stdout.read1())

proc.stdin.close()
proc.wait()
print(proc.stdout.read())
