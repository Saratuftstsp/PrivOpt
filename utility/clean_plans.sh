#!/bin/bash

'''# Check if the user provided an argument
if [ -z "$1" ]; then
    echo "Please provide an argument."
    exit 1
fi

# Store the argument in a variable
argument=$1'''

# List of inputs to pass to the Python script
inputs=("bsl1_all_erased" "bsl2_all_true" "mcv_avail" "mcv_hide")

# Loop over inputs and call Python script with each
for input in "${inputs[@]}"; do
    # Split the input pair into two variables
    #input1=$(echo $input_pair | cut -d' ' -f1)
    #input2=$(echo $input_pair | cut -d' ' -f2)
    
    # Call the Python script with both inputs
    python3 clean_plans.py "$input" #"$argument"
done