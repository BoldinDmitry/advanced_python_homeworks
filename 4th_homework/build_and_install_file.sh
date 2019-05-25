#!/bin/bash

rm -rf build/
python setup.py build
python setup.py install
python main.py