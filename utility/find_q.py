import psycopg2
import time
import os
from tqdm import tqdm
import random

        
        
def get_queries():
    query_files_dir = "/Users/saraalam/Desktop/PrivOptCode/job/"
    fnames = [f for f in os.listdir(query_files_dir) if os.path.isfile(os.path.join(query_files_dir, f))]
    num_qs = len(fnames)
    print(num_qs)
    
    temp = []
    for i in range(len(fnames)):
        fname = fnames[i]
        if fname!="fkindexes.sql" and fname!="schema.sql":
            temp.append(fname)
    fnames = temp

    q_dict = {}
    for i in range(5): #range(len(fnames))
        idx = random.randint(0, num_qs-1)
        fname = fnames[idx]
        f = open(query_files_dir+fname, "r")
        q = ""
        for _ in f.readlines():
            q+= _.strip()+" "
        q_dict[fname] = q
        q= ""
        f.close()
    #print(q_dict)
    return q_dict

def find_longest_times(cursor, q_dict):
    longest_running_queries = []
    
    runtime_dict = {}
    runtimes = []
    # tqdm(len(q_dict))
    key_lst = []
    for key in q_dict:
        key_lst.append(key)
        
    for i in tqdm(range(len(key_lst))):
        qfile = key_lst[i]
        print(qfile)
        q = q_dict[qfile]
        exec_time = int(get_execution_time(cursor, q))
        if exec_time not in runtime_dict:
            runtimes.append(exec_time)
            runtime_dict[exec_time] = []
        runtime_dict[exec_time].append(qfile)

    runtimes.sort()
    
    longest_runtimes = []
    for i in range(len(runtimes)):
        longest_runtimes.append(runtimes[len(runtimes)-1-i])
        
        
    longest_runtimes2 = []
    numqs = 0
    i = 0
    while numqs <= 9:
        if i >= len(longest_runtimes):
            break
        runtime = longest_runtimes[i]
        qfiles = runtime_dict[runtime]
        for qfile in qfiles:
            longest_running_queries.append(qfile)
            longest_runtimes2.append(runtime)
            numqs+=1
            if numqs >= 9:
                break
        i += 1
    
    return longest_running_queries, longest_runtimes2

    
def save_query_plan(cursor, q, fname):
    cursor.execute(f"EXPLAIN {q}")
    execution_plan = cursor.fetchall()
    
    exec_plans_f_path = "/Users/saraalam/Desktop/PrivOptCode/experiment/bsl1_all_erased/exec_plans/"
    exec_plan_fname = "plan_"+fname+".txt"
        
    
    if not os.path.exists(exec_plans_f_path):
        os.makedirs(exec_plans_f_path)  # Create the directory if it doesn't exist

    f2 = open(exec_plans_f_path+exec_plan_fname, "w")
    
    for _ in execution_plan:
        f2.write(str(_))
        f2.write("\n")
        
    f2.close()


def save_execution_times(execution_times):
    '''
    Given a dictionary of query runtimes
    Write each (query_name, avg_runtime) pair to a file
    '''
    exec_times_fpath = "/Users/saraalam/Desktop/PrivOptCode/experiment/bsl1_all_erased/"
    exec_times_fname = exec_times_fpath + "exec_times.txt"
    if not os.path.exists(exec_times_fpath):
        os.makedirs(exec_times_fpath)  # Create the directory if it doesn't exist
    f = open(exec_times_fname, "w")
    for qname in ["1a", "2a", "3a", "4a", "5a"]:
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
    query_files = ["1a", "2a", "3a", "4a", "5a"]
    exec_times = {}

    for fname in query_files:
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
    for i in tqdm(range(10)):
        cursor.execute(q)
    end=time.time()
    avg_exec_time = (end-start)/10
    return avg_exec_time



    
def main():
    # Database connection parameters
    db_info = {
        'dbname': 'imdb',
        'user': 'postgres',
        'password': '1908',
        'host': 'localhost',
        'port': '5433'
    }
    
    try:
        # Connect to the PostgreSQL database
        connection = psycopg2.connect(**db_info)
        cursor = connection.cursor() # object needed to refer to connection
    
        
        s = time.time()
        
        q_dict = get_queries()
        '''for q in q_dict:
            print(q)
            print(q_dict[q])
            cursor.execute(q_dict[q])
            print(len(cursor.fetchall()))
            print("________________________\n")
            break'''
        longest_running_queries, longest_runtimes2 = find_longest_times(cursor, q_dict)
        
        print(longest_running_queries)
        print("\n\n")
        print(longest_runtimes2)
            
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