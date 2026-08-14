from camdesign import create_app
from camdesign.devserver import run_development_server

if __name__ == "__main__":
    raise SystemExit(run_development_server(create_app))


app = create_app()
