# model_maker
Generate Python, TypeScript, or C# models from a JSON data file

# Installation

## Prereqs

* Python3.9+

## Steps

1. Create a virtual environment (venv)
1. Activate the venv
1. `pip install -r requirements.txt`

# Example usage

Given some JSON file (crafted manually, or pulled from an http request, etc) called `path/to/data.json`...

```bash
python main.py --path path/to/data.json --outdir path/to/out/ python
```
