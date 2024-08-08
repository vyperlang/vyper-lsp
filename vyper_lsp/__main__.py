import argparse
from .main import server


def main():
    parser = argparse.ArgumentParser(
        description="Start the server with specified protocol and options."
    )
    parser.add_argument("--stdio", action="store_true", help="Use stdio protocol")
    parser.add_argument(
        "--tcp",
        nargs=2,
        metavar=("HOST", "PORT"),
        help="Use TCP with specified host and port",
    )

    args = parser.parse_args()

    if args.tcp:
        print("Starting server with TCP")
        host, port = args.tcp
        server.start_tcp(host=host, port=int(port))
    else:
        print("Starting server with stdio protocol")
        # Default to stdio if --tcp is not provided
        server.start_io()


if __name__ == "__main__":
    main()
