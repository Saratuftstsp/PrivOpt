import psycopg2
import time
import os

        
        
def get_query(fname):
    query_files_dir = "/Users/saraalam/Desktop/PrivOptCode/job/"
    f = open(query_files_dir+fname+".sql", "r")
    q = ""
    for _ in f.readlines():
        q+= _.strip()+" "
    f.close()
    return q
    
def save_query_plan(cursor, q, fname):
    cursor.execute(f"EXPLAIN {q}")
    execution_plan = cursor.fetchall()
    
    exec_plans_f_path = "/Users/saraalam/Desktop/PrivOptCode/experiment/mcv_noised/exec_plans/"
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
    exec_times_fpath = "/Users/saraalam/Desktop/PrivOptCode/experiment/mcv_noised/"
    exec_times_fname = exec_times_fpath + "exec_times.txt"
    if not os.path.exists(exec_times_fpath):
        os.makedirs(exec_times_fpath)  # Create the directory if it doesn't exist
    f = open(exec_times_fname, "w")
    for qname in ["6a", "13a", "16d", "17b", "25c", "17c", "28a", "26a", "27c", "19d"]:
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
    query_files = ["6a", "13a", "16d", "17b", "25c", "17c", "28a", "26a", "27c", "19d"]
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
    for i in range(10):
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
        
        #1.
        # Get the queries to run
        # And save the query plans for each
        query_files = ["6a", "13a", "16d", "17b", "25c", "17c", "28a", "26a", "27c", "19d"]
        q_dict = {}
        for fname in query_files:
            q = get_query(fname)
            save_query_plan(cursor, q, fname)
            q_dict[fname] = q
            
        exec_times = run_queries(cursor, q_dict)
        
        save_execution_times(exec_times)
            
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