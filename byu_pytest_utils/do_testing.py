import asyncio
import os

async def worker(exec, inputs):
    exec = ['python', 'worker.py', 'student_file.py']
    inputs = ['input1\n', 'input2\n', 'input3\n', '\n']

    # Create a new environment dictionary
    env = os.environ.copy()
    env.update({"INPUTS": ''.join(inputs)})

    # Create the subprocess with the custom environment
    proc = await asyncio.create_subprocess_exec(
        *exec, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        env=env)

    # Read the output from the worker program
    output = await proc.stdout.read()
    error = await
    await proc.wait()

    print(output.decode())


if __name__ == '__main__':
    asyncio.run(worker('student_file.py', ['input1\n', 'input2\n', 'input3\n', '\n']))