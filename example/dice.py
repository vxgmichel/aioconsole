"""Run a CLI to simulate dice throws."""

import random
import asyncio
import argparse

from aioconsole import AsynchronousCli


@asyncio.coroutine
def dice(reader, writer, faces):
    for _ in range(3):
        yield from asyncio.sleep(0.33)
        writer.write('.')
        yield from writer.drain()
    writer.write('\n')
    return random.randint(1, faces)


def main():
    parser = argparse.ArgumentParser(description='Throw a dice.')
    parser.add_argument('--faces', '-f', metavar='N', type=int,
                        default=6, help='Number of faces')
    cli = AsynchronousCli({'dice': (dice, parser)}, prog='dice')

    loop = asyncio.get_event_loop()
    loop.run_until_complete(cli.interact())


if __name__ == "__main__":
    main()
