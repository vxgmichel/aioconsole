"""Command line interface for echo server."""

import fnmatch
import asyncio
import argparse

from aioconsole import AsynchronousCli, start_interactive_server
from aioconsole.server import parse_server, print_server

from . import echo


async def get_history(reader, writer, pattern=None):
    history = asyncio.get_event_loop().history
    if not history:
        return "No message in the history"
    if pattern:
        history = {host: history[host] for host in fnmatch.filter(history, pattern)}
    if not history:
        return "No host match the given pattern"
    for host in history:
        writer.write("Host {}:\n".format(host).encode())
        for i, message in enumerate(history[host]):
            writer.write("  {}. {}\n".format(i, message).encode())


def make_cli(streams=None):
    parser = argparse.ArgumentParser(description="Display the message history")
    parser.add_argument("--pattern", "-p", type=str, help="pattern to filter hostnames")
    commands = {"history": (get_history, parser)}
    return AsynchronousCli(commands, streams, prog="echo")


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Run the echo server and a command line interface."
    )
    parser.add_argument(
        "server",
        metavar="[HOST:]PORT",
        type=str,
        help="interface for the echo server, default host is localhost",
    )
    parser.add_argument(
        "--serve-cli",
        metavar="[HOST:]PORT",
        type=str,
        help="serve the command line interface on the given host+port "
        "instead of using the standard streams",
    )
    namespace = parser.parse_args(args)
    host, port = parse_server(namespace.server, parser)
    if namespace.serve_cli is not None:
        serve_cli = parse_server(namespace.serve_cli, parser)
    else:
        serve_cli = None
    return host, port, serve_cli


def main(args=None):
    host, port, serve_cli = parse_args(args)
    if serve_cli:
        cli_host, cli_port = serve_cli
        coro = start_interactive_server(make_cli, cli_host, cli_port)
        server = asyncio.get_event_loop().run_until_complete(coro)
        print_server(server, "command line interface")
    else:
        asyncio.ensure_future(make_cli().interact())
    return echo.run(host, port)


if __name__ == "__main__":
    main()
