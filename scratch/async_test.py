import asyncio


async def read(stream):
    buffer = []
    while True:
        try:
            token = await asyncio.wait_for(stream.read(1), 1)
            if not token:
                break
            buffer.append(token.decode())
        except asyncio.TimeoutError:
            break
    
    return ''.join(buffer)
       
    
async def test():
    print('foo')
    proc = await asyncio.subprocess.create_subprocess_shell(
            "python -c '[print(input(\"thing: \")) for _ in range(5)]'", 
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
        )
    for inp in ['cat', 'bat', 'cow', 'cage', 'foo']:
        print(await read(proc.stdout), end='')
        proc.stdin.write((inp + '\n').encode())
        print(inp)
        await proc.stdin.drain()
    
    print(await read(proc.stdout), end='')
    await proc.wait()

    
asyncio.run(test())
