# CodeGuard

A desktop application that monitors important files inside a software project so developers can detect (and review) unexpected changes.

## Why

In the current AI coding era, AI assistants, scripts, and automation tools frequently modify project files. That is often useful, but it can also silently change critical files (`.env`, dependency manifests, Dockerfiles, migrations, generated mocks…). CodeGuard lets you snapshot a trusted state of a project and later see exactly what changed, with severity-aware contextual alerts for the files that matter most.

## Status

Early development. Built incrementally

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt` (`customtkinter`). SQLite is part of the Python standard library.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

The GUI will be wired up in a later stage. For now, `main.py` only verifies the project layout is correct.

## License

For educational use (college Object-Oriented Programming project).
