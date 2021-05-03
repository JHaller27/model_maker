#!/usr/bin/env bash

. venv/bin/activate
pyinstaller ./main.py --onefile --paths venv/lib/python3.9/site-packages/
deactivate

