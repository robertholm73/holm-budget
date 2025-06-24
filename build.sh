#!/bin/bash
# Clear pip cache and install fresh dependencies
pip cache purge
pip uninstall -y psycopg2 psycopg2-binary
pip install -r requirements.txt --no-cache-dir