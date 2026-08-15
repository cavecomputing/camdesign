import argparse

from camdesign import create_app
from camdesign.devserver import run_development_server

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=None, help="Port to serve on (default: 5000)")
    args = parser.parse_args()
    raise SystemExit(run_development_server(create_app, port=args.port))


app = create_app()
