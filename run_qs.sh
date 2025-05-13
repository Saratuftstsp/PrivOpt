#!/bin/bash

# List of strings
inputs=("1a" "2a")

# Loop through each string and call the Python script
for item in "${inputs[@]}"
do
  ./restore.sh
  timeout 900s python3 run_given_qs.py oblivious "$item"
done