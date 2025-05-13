import psycopg2
import time
import os
import argparse
from tqdm import tqdm

'''
This script takes two arguments: 
1. case: scenario in which queries are being run
Eg: only nullfrac is "erased" and everything else is left unmodified, so the case could be called pub_ex_nullfrac (i.e all of system catalog is public except nullfrac)
2. qlist_com_sep: comma separated list of query names, no spaces
Eg: if I want to run queries 1a-5a, I would pass in 1a,2a,3a,4a,5a as the second argument, WITHOUT spaces

The script runs the specified queries and stores the average time of 10 runs in a text file and also stored the query plans.
It does NOT run ANALYZE after running the queries, so the system catalog is not modified in any way.

Potential reasons for errors:
Might need to respecify the hard-coded path for the directory where the queries are located if repo is cloned elsewhere.
'''
        
        
def get_query(fname):
    query_files_dir = "/Users/saraalam/Desktop/PrivOptCode/job/"
    f = open(query_files_dir+fname+".sql", "r")
    q = ""
    for _ in f.readlines():
        q+= _.strip()+" "
    f.close()
    return q
    
def save_query_plan(cursor, q, case, fname):
    cursor.execute(f"EXPLAIN {q}")
    execution_plan = cursor.fetchall()
    
    exec_plans_f_path = str(os.getcwd()) + "/plans/"+ case +"/"
    exec_plan_fname = case+"_"+fname+".txt"
        
    
    if not os.path.exists(exec_plans_f_path):
        os.makedirs(exec_plans_f_path)  # Create the directory if it doesn't exist

    f2 = open(exec_plans_f_path+exec_plan_fname, "w")
    
    for _ in execution_plan:
        f2.write(str(_))
        f2.write("\n")
        
    f2.close()


def save_execution_times(execution_times, case):
    '''
    Given a dictionary of query runtimes
    Write each (query_name, avg_runtime) pair to a file
    '''
    exec_times_fpath = str(os.getcwd()) + "/"
    exec_times_fname = exec_times_fpath+ "rtimes_" + case + ".txt"
    if not os.path.exists(exec_times_fpath):
        os.makedirs(exec_times_fpath)  # Create the directory if it doesn't exist
    f = open(exec_times_fname, "a")
    for qname in list(execution_times.keys()):
        exec_time_for_q = execution_times[qname]
        f.write(qname + " " + str(exec_time_for_q)+"\n")
    f.close()
    


def run_queries(cursor, q_dict):
    '''
    Given a dictionary of query strings
    For each query
    Call get_execution_time to get the average time of 10 runs
    Store it in a dictionary where 
        the keys of the query dictionary
        and the values are the average runtime of 10 runs of the query
    Return the dictionary of average runtimes for each query
    '''
    #query_files = list(q_dict.keys)
    exec_times = {}
    print("Running queries to get execution times.")
    for fname in tqdm(list(q_dict.keys())):
        print("Running query "+fname+".")
        q = q_dict[fname]
        avg_exec_time = get_execution_time(cursor, q)
        exec_times[fname] = avg_exec_time
        
    return exec_times


        
def get_execution_time(cursor, q):
    '''
    Given a query string, execute the query 10 times
    Return the average time for the 10 runs
    '''
    start = time.time()
    for i in range(10):
        cursor.execute(q)
    end=time.time()
    avg_exec_time = (end-start)/10
    return avg_exec_time



    
def main():
    parser = argparse.ArgumentParser(description='Queries to run.')
    parser.add_argument('case', type=str, help='Name of the scenario it is, eg: oblivious_w_noisy_nullfrac')
    parser.add_argument('qlist_com_sep', type=str, help='Names of queries to run, delimited by commas, no spaces.')
    
    args = parser.parse_args()
    
    # Database connection parameters
    db_info = {
        'dbname': 'imdb',
        'user': 'saraalam',
        'password': 'papp17',
        'host': 'localhost',
        'port': '5432'
    }
    
    try:
        # Connect to the PostgreSQL database
        connection = psycopg2.connect(**db_info)
        cursor = connection.cursor() # object needed to refer to connection
        #cursor.execute("analyze") DO NOT DO THIS BECAUSE THE ERASNG IS DONE BY A SEPARATE SCRIPT
        
        s = time.time()
        
        #1.
        # Get the queries to run
        # And save the query plans for each
        query_files = (args.qlist_com_sep).strip().split(",") #["28a", "29a"]
        q_dict = {}
        print("Saving query plans.")
        for fname in tqdm(query_files):
            q = get_query(fname)
            save_query_plan(cursor, q, args.case, fname)
            q_dict[fname] = q
        
        exec_times = run_queries(cursor, q_dict)
        
        save_execution_times(exec_times, args.case)
        
        #cursor.execute("analyze") # run analyze here since we should restore the erased system catalog
        #print(os.getcwd())
        end= time.time()
        print("Time taken: ", end-s)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the cursor and connection
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    
    

if __name__ == '__main__':
    main()