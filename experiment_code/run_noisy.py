import psycopg2
import time
import os
import argparse
from tqdm import tqdm
import numpy as np

'''
This script takes three arguments: 
1. case: scenario in which queries are being run
Eg: only nullfrac is "noised" and everything else is erased, so the case could be called ob_wn_nullfrac (i.e all of system catalog is erased and nullfrac is noisy)
2. noised_cols: comma separated list of columns in pg_statistic to which noise must be added
Eg: if null_frac and correlation need to be noised then pass in "null_frac,correl", WITHOUT spaces
Currently, only following inputs supported: ["nullfrac", "correl", "ndist"]
3. qlist_com_sep: comma separated list of query names, no spaces
Eg: if I want to run queries 1a-5a, I would pass in 1a,2a,3a,4a,5a as the second argument, WITHOUT spaces

The script runs the specified queries and stores the average time of 10 runs in a text file and also stored the query plans.

Potential reasons for errors:
Might need to respecify the hard-coded path for the directory where the queries are located if repo is cloned elsewhere.
'''


#_________________________________________________________________METHODS TO GET ROWS TO CHANGE AND ADD NOISE FOR GIVEN EPSILON______________________________________________________________________________________________________________________________________________

def add_laplace_noise(noised_col, data, epsilon, offsets = [], sensitivity=1):
    """
    Adds Laplace noise to a list of values for differential privacy.
    
    Parameters:
    - float[]: data
    - float: epsilon
    - float: sensitivity
    
    Returns:
    - list of float values with added Laplace noise
    """
    # Calculate the scale (b) for the Laplace distribution
    scale = sensitivity / epsilon
    
    # Generate Laplace noise
    noise = np.random.laplace(0, scale, len(data))  # ensure this is the number of rows
    
    # Add noise to the original data
    noisy_data = [value + abs(n) for value, n in zip(data, noise)]
    
    # Correct for null correl rows
    if noised_col == "correl":
        for i in range(len(data)):
            offset = offsets[i]
            if offset == -1:
                noisy_data[i] = data[i]

    
    return noisy_data



def getStatRows(cursor):
    """
    Gets all the rows of pg_statistic that belong to the "public" namespace

    Parameters:
    psycopg2.extensions.connection: connection
    psycopg2.extensions.cursor: cursor

    Returns:
    rows of pg_statistic

    """
    # Create the new table pg_statistics_noisy
    copy_public_namespace_stat_query = '''
    select * from pg_statistic s where s.starelid in
    (select c.oid as starelid from pg_class c join pg_namespace n on c.relnamespace=n.oid where n.nspname='public')
    ''' # and n.nspname not like 'pg' and n.nspname not like 'sql')
    
    # Execute the query to create the new table
    cursor.execute(copy_public_namespace_stat_query)
    rtc = cursor.fetchall()
    
        

    #print("Rels from namespace == public fetched successfully.\n\n")
    
    return rtc


# correl in pg_stats only has a value if SOME stakindN is 3 and the corresponding stavaluesN has an array with a single value in it
# if no such values exist then these rows of pg_stats do not have correl
# find the offset from stakind1 where the 3 occurs, if it does occur at all, otherwise set the offset to -1
def find_correl_offset(row):
    for field_idx in [6, 7, 8, 9, 10]:
        if row[field_idx]==3:
            return field_idx - 6
    return -1

def get_num_rows(relid, cursor):
    q1 = f'''select c.relname from pg_class c join pg_statistic s on c.oid=s.starelid where s.starelid={relid} limit 1'''
    cursor.execute(q1)
    tablename = cursor.fetchall()[0][0]
    
    q2 = f'''select count(*) from {tablename};'''
    cursor.execute(q2)
    num_rows = cursor.fetchall()[0][0]

    
    '''if relid==16465:
        print(tablename, num_rows)'''
    
    return num_rows
    

# get the original values of the columns to be noised
# should only be called once and passed to functions to add noise and create noisy versions of the rtc
def get_noised_col_vals(rtc, noised_col, cursor):
    vals_lst = []
    if noised_col=="correl":
        for row in rtc:
            offset = find_correl_offset(row)
            if offset == -1:
                vals_lst.append(-1)
            else:
                vals_lst.append(row[21+offset])
        return vals_lst


    if noised_col =="nullfrac":
        unknown_tables = []
        for row in rtc:
            idx_oi = float(row[3])
            try:
                num_rows = get_num_rows(row[0], cursor)
            except Exception as e:
                unknown_tables.append((row[0], row[1], row[2]))
                pass
            val = idx_oi * int(num_rows)
            vals_lst.append(val)
        
    elif noised_col == "ndist":
        for row in rtc:
            vals_lst.append(row[5])
    #print(len(unknown_tables))
    return vals_lst

# Noise specified columns and erase the rest
def insert_noise_into_rtc(rtc, noised_col_lst, col_vals_dict, cursor):
   
    # 1. divide epsilon among columns to be noised
    epsilon = 0.1
    num_noised_col = len(noised_col_lst)
    epsilon_per_col = epsilon/num_noised_col
    num_rows = len(rtc)
    epsilon_per_row = epsilon_per_col/num_rows
    num_rows_null_correl = 0
    print(f"Epsilon per i.i.d : {epsilon_per_row}\n Number of rows: {num_rows}")
    
    # 2. if correl needs to be noised, we will need the offsets
    offsets_per_row = []
    if "correl" in noised_col_lst:
        for row_idx in range(num_rows):
            offsets_per_row.append(find_correl_offset(rtc[row_idx]))
    # add noise to the original values of the columns to be noised
    noisy_vals_dict = {}
    for noised_col in noised_col_lst:
        vals_lst = col_vals_dict[noised_col]
        noisy_vals_lst = add_laplace_noise(noised_col, vals_lst, epsilon_per_row, offsets_per_row)
        noisy_vals_dict[noised_col] = noisy_vals_lst

        
    # 3. create noisy version of each rtc and store in changed_rtc list
    changed_rtc = []
    row_len = len(rtc[0])
    for row_idx in range(num_rows):
        # does this row have a correl?
        correl_offset=-1
        if ("correl" in noised_col_lst):
            correl_offset = offsets_per_row[row_idx]
        
        if ("correl" in noised_col_lst) and correl_offset==-1: num_rows_null_correl += 1
        
        new_row = tuple()
        for field_idx in range(row_len):
            
            if field_idx == 3:
                if "nullfrac" not in noised_col_lst:
                    new_row = new_row + (0,) # mask for nullfrac 0
                else:
                    noisy_count = noisy_vals_dict["nullfrac"][row_idx]
                    total_count = get_num_rows(rtc[row_idx][0], cursor)
                    noisy_frac = noisy_count/total_count
                    new_row = new_row + (noisy_frac,)
                
            elif field_idx == 5:
                if "ndist" not in noised_col_lst:
                    new_row = new_row + (0,) # mask for ndistinct 0
                else:
                    #new_row = new_row + (rtc[row_idx][field_idx],)
                    new_row = new_row + (noisy_vals_dict["ndist"][row_idx],)
                    
            elif 6 <= field_idx <= 10:
                if (correl_offset != -1) and (field_idx == 6 + correl_offset):
                    new_row = new_row + (rtc[row_idx][field_idx],)
                else:
                    new_row = new_row + (0,)
            # only stanumbers should be changed and stakindN should remain 3
            elif 21<= field_idx <= 25:
                if (correl_offset != -1) and (field_idx == 21 + correl_offset):
                    #new_row = new_row + (rtc[row_idx][field_idx],)
                    new_row = new_row + (noisy_vals_dict["correl"][row_idx],)
                else:
                    new_row = new_row + (None,)
                
            elif 26<= field_idx <= 30:
                #field_val = rtc[row_idx][field_idx]
                new_row = new_row + (None,)
                
            else: 
                # includes prim key, stawidth, staop, stacol 
                # can't include stakindN because that is tied to stanumbers
                new_row = new_row + (rtc[row_idx][field_idx],)
                
        changed_rtc.append(new_row)
    print(f"Assumed extra draws for correl: {num_rows_null_correl}")
    return changed_rtc

def get_col_counts(relid, attnum, cursor):
    q1 = f'''select c.relname from pg_class c join pg_statistic s on c.oid=s.starelid where s.starelid={relid} limit 1'''
    cursor.execute(q1)
    tablename = cursor.fetchall()[0][0]
    #print(tablename)
    q2 = f'''select a.attname from pg_class c join pg_attribute a on c.oid=a.attrelid where a.attrelid={relid} and a.attnum={attnum}'''
    cursor.execute(q2)
    attname = cursor.fetchall()[0][0]
    #print(attname)
    
    q = f'''select {attname}, count(*) c from {tablename} group by {attname} order by c desc'''
    
    cursor.execute(q)
    
    vals_and_counts = cursor.fetchall()
    vals, counts = clean_vals_and_counts(vals_and_counts)

    
    return vals, counts

def clean_vals_and_counts(vals_raw):
    return vals_raw.strip("{}").split(",")

def insert_cr_into_pg_statistic(rtc, cr, connection, cursor):
    col_names = ["stanullfrac", "stawidth", "stadistinct", "stakind1", "stakind2","stakind3", "stakind4", "stakind5", "staop1", "staop2", "staop3", "staop4", "staop5", "stacoll1", "stacoll2", "stacoll3", "stacoll4", "stacoll5", "stanumbers1", "stanumbers2", "stanumbers3", "stanumbers4", "stanumbers5", "stavalues1", "stavalues2", "stavalues3", "stavalues4", "stavalues5"]
    for row_idx in range(len(cr)):
        for j in range(3, 31): # we're doing this for indexes 3 through to 30 of the rows
            field_val = cr[row_idx][j]
            try:
                if field_val == None:
                    q = """
                        UPDATE pg_statistic
                        SET """ + col_names[j-3] + """ = %s
                        WHERE starelid = %s
                        and staattnum = %s
                        and stainherit = %s
                    """
                    cursor.execute(q, (None, cr[row_idx][0], cr[row_idx][1], cr[row_idx][2]))  # indexes 0, 1 and 2 of the row, together, form the primary key
                
                else:
                    q = '''
                    update pg_statistic set {}={} where starelid={} and staattnum={} and stainherit = {};
                    '''.format(col_names[j-3], field_val, cr[row_idx][0], cr[row_idx][1], cr[row_idx][2])
                    cursor.execute(q)
            except Exception as e:
                print(j)
                print(col_names[j-3])
                print(field_val)
            # Commit the transaction(s)
            connection.commit()


#_________________________________________________________________METHODS TO GET AND RUN QUERIES AND SAVE PLANS AND EXECUTION TIMES__________________________________________________________________________________________________________________________________________   
def get_query(fname):
    query_files_dir = "/Users/saraalam/Desktop/PrivOptCode/job/"
    f = open(query_files_dir+fname+".sql", "r")
    q = ""
    for _ in f.readlines():
        q+= _.strip()+" "
    f.close()
    return q
    
def save_query_plan(cursor, q, run, case, fname):
    cursor.execute(f"EXPLAIN {q}")
    execution_plan = cursor.fetchall()
    
    exec_plans_f_path = str(os.getcwd()) + "/plans/"+ case +"/" + str(run) + "/"
    exec_plan_fname = case+"_"+fname+".txt"
        
    
    if not os.path.exists(exec_plans_f_path):
        os.makedirs(exec_plans_f_path)  # Create the directory if it doesn't exist

    f2 = open(exec_plans_f_path+exec_plan_fname, "w")
    
    for _ in execution_plan:
        f2.write(str(_))
        f2.write("\n")
        
    f2.close()


def save_execution_times(execution_times, case, run):
    '''
    Given a dictionary of query runtimes
    Write each (query_name, avg_runtime) pair to a file
    '''
    exec_times_fpath = str(os.getcwd()) + "/"+ case + "_runs/"
    exec_times_fname = exec_times_fpath+ f"rtimes_run{run}_" + case + ".txt"
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
    for i in tqdm(range(10)):
        cursor.execute(q)
    end=time.time()
    avg_exec_time = (end-start)/10
    return avg_exec_time



    
def main():
    parser = argparse.ArgumentParser(description='Queries to run.')
    parser.add_argument('case', type=str, help='Name of the scenario it is, eg: oblivious_w_noisy_nullfrac')
    parser.add_argument('noised_cols', type=str, help='Name(s) of column(s) to not mask since it will be noised. Comma-separated. Enter random string if nothing is noised/everything needs to be masked/hidden.')
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
        query_files = (args.qlist_com_sep).strip().split(",") #["28a", "29a"]
        q_dict = {}
        for fname in tqdm(query_files):
                q = get_query(fname)
                q_dict[fname] = q
        
        #2. Get the rows that need to be changed, only once and retain the original values for different iterations of noise addition
        rtc = getStatRows(cursor)
        print("Got rtcs.")
       
     
         
        #3. Get original values of the columns to be noised
        noised_col_lst = args.noised_cols.strip().split(",")
        col_vals_dict = {}
        for noised_col in noised_col_lst:
            vals_lst = get_noised_col_vals(rtc, noised_col, cursor)
            col_vals_dict[noised_col] = vals_lst

        for i in range(10):
            int_start = time.time()
            #4. Add noise
            cr = insert_noise_into_rtc(rtc, noised_col_lst, col_vals_dict, cursor)
            print("Changed rows.")
            insert_cr_into_pg_statistic(rtc, cr, connection, cursor)
            #print("Inserted noisy/masked rows into pg_statistic.")
        
            #5.
            # For each noise addition, save query plan
            print(f"Saving query plans, run {i}.")
            for fname in tqdm(query_files):
                q = q_dict[fname]
                save_query_plan(cursor, q, i, args.case, fname)
        
            #6. Run queries 10 times to get to average execution times
            exec_times = run_queries(cursor, q_dict)
        
            #7. Save execution times to a file
            save_execution_times(exec_times, args.case, i)
            
            int_end = time.time()
            print(f"Time taken for run {i} : {(int_end - int_start)}")
        

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
    
