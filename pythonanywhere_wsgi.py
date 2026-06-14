# This file contains the WSGI configuration for PythonAnywhere
# DO NOT RUN THIS FILE LOCALLY.
# 
# Follow the walkthrough to paste this code into your PythonAnywhere Web tab.

import sys
import os

# 1. Provide the exact path to your project folder on PythonAnywhere
# Replace 'yourusername' with your actual PythonAnywhere username
project_home = '/home/yourusername/image-scraper'

if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# 2. Set environment variables if needed (optional)
# os.environ['MY_VAR'] = 'my_value'

# 3. Import the Flask app object from your app.py file
# PythonAnywhere uses this `application` variable to serve your site.
from app import app as application
