import psycopg2
import numpy as np
import time

            
def copy_orig_pg_statistics(connection, cursor):
    # Create the new table pg_statistics_noisy
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS pg_statistics_cpy AS
    SELECT * FROM pg_statistic;
    '''
    
     # Execute the query to create the new table
    cursor.execute(create_table_query)
        
    # Commit the transaction
    connection.commit()
    

    print("Table pg_statistics_cpy created successfully.")
    
    
def getStatRows(connection, cursor):
    """
    Gets all the rows of pg_statistic that belong to the public namespace

    Parameters:
    psycopg2.extensions.connection: connection
    psycopg2.extensions.cursor: cursor

    Returns:
    rows of pg_statistic

    """
    # Create the new table pg_statistics_noisy
    copy_public_namespace_stat_query = '''
    select * from pg_statistic s where s.starelid in
    (select c.oid as starelid from pg_class c join pg_namespace n on c.relnamespace=n.oid)
    '''
    
    # Execute the query to create the new table
    cursor.execute(copy_public_namespace_stat_query)
        
    # Commit the transaction
    connection.commit()
    print("Rels from namespace == public fetched successfully.\n\n")
    
    return cursor.fetchall()
    
def add_laplace_noise(data, epsilon, sensitivity=1):
    """
    Adds Laplace noise to a list of values for differential privacy.
    
    Parameters:
    - float: data
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
    noisy_data = [value + n for value, n in zip(data, noise)]
    
    return noisy_data

def add_laplace_noise_arr(data, epsilon):
    noisy_vals = []
    for orig_val_lst in data:
        if (orig_val_lst != None):
            noisy_vals.append(add_laplace_noise(orig_val_lst, epsilon))
        else:
            noisy_vals.append(orig_val_lst)

def insert_vals_into_rtc(noisy_vals, rtc, col_idx):
    # copy everything, except index 3, which comes from noisy_vals
    changed_rtc = []
    row_len = len(rtc[0])
    for row_idx in range(len(rtc)):
        new_row = tuple()
        for field_idx in range(row_len):
            if field_idx==col_idx:
                new_row = new_row + (noisy_vals[row_idx], )
            else:
                new_row = new_row + (rtc[row_idx][field_idx],)
        changed_rtc.append(new_row)
        
    print("Sanity check: ")
    print("numrows {} and numcols {} in rtc.".format(len(rtc), len(rtc[0])))
    print("Example orig_val: {}.".format(rtc[3][3]))
    print("numrows {} and numcols {} in changed_rtc.".format(len(changed_rtc), len(changed_rtc[0])))
    print("Example orig_val: {}.".format(changed_rtc[3][3]))
    print("\n\n")
    
    return changed_rtc
    
def insert_cr_into_pg_statistic(cr, connection, cursor):
    print("Sanity check:\n")
    probe_pg_statistic(connection, cursor)
    print("\n")
    for row_idx in range(len(cr)):
        q_insert_noisy_val = '''
        update pg_statistic set stanullfrac={} where starelid={} and staattnum={} and stainherit = {};
        '''.format(cr[row_idx][3], cr[row_idx][0], cr[row_idx][1], cr[row_idx][2])
        cursor.execute(q_insert_noisy_val)
        
        # Execute the query to create the new table
        cursor.execute(q_insert_noisy_val)
        
        # Commit the transaction
        connection.commit()
    probe_pg_statistic(connection, cursor)
    print("\n\n")
        
            
    
            
def change_pg_statistics(connection, cursor, epsilon=0.1):
    
    #1.
    # Get rows of pg_statistic that we want to change
    # i.e rows that belong to the namespace 'public'
    # these are the user-created table's stat rows
    # rtc == rows to change
    rtc = getStatRows(connection, cursor)
    
    orig_vals1 = get_orig_vals(rtc, 3) # col_idx = 3 is null_frac
    orig_vals2 = get_orig_vals(rtc, 5) # col_idx = 5 is n_distinct
    orig_vals3 = get_orig_vals(rtc, 21) # col_idx = 21 is 
 
    
    
    #2.
    # Add noise to a specific single-numeric_value column
    noisy_vals1 = add_laplace_noise(orig_vals1, epsilon)  #transform statistics()
    noisy_vals2 = add_laplace_noise(orig_vals2, epsilon)  #transform statistics()
    noisy_vals3 = add_laplace_noise_arr(orig_vals3, epsilon)  #transform statistics()
        
    #3.
    # insert the noisy value into pg_statistic
    # cr = changed rows
    cr = insert_vals_into_rtc(noisy_vals1, rtc, 3)
    cr = insert_vals_into_rtc(noisy_vals2, cr, 5)
    cr = insert_vals_into_rtc(noisy_vals3, cr, 21)
    insert_cr_into_pg_statistic(cr, connection, cursor)
    
    #4.
    # run queries and save plans and execution times
    run_queries(cursor, 1, epsilon)
    
    #5. undo change
    cursor.execute("analyze")
    
def get_orig_vals(rtc, col_idx):
    orig_vals = []
    r_idx = 0
    for r in rtc:
        orig_vals.append(rtc[r_idx][col_idx])
        r_idx+=1
    return orig_vals

        
        
def get_query(fname):
    query_files_dir = "/Users/saraalam/Desktop/PrivOptCode/job/"
    f = open(query_files_dir+fname+".sql", "r")
    q = ""
    for _ in f.readlines():
        q+= _.strip()
    f.close()
    return q
    
def save_query_plan(cursor, q, fname, noisy, eps):
    cursor.execute(f"EXPLAIN {q}")
    execution_plan = cursor.fetchall()
    
    if (noisy==0):
        f2 = open("exec_plans/plan_"+fname+".txt", "w")
    else:
        f2 = open("exec_plans/plan_"+fname+"_noisy_"+str(eps)+".txt", "w")

    for _ in execution_plan:
        f2.write(str(_))
        f2.write("\n")
        
    f2.close()
    
def get_execution_time(cursor, q):
    start = time.time()
    for i in range(10):
        cursor.execute(f"EXPLAIN {q}")
        execution_plan = cursor.fetchall()
        cursor.execute(q)
        output = cursor.fetchall()
    end=time.time()
    exec_time = (end-start)/10
    return exec_time

def run_queries(cursor, noisy=0, eps=0):
    #query_files_dir = "/Users/saraalam/Desktop/PrivOptCode/job/"
    query_files = ["1a", "2a", "3a", "4a", "5a"]
    
    if (noisy==0):
        f3 = open("exec_times.txt", "w")
    else:
        f3 = open("exec_times_noisy_"+str(eps)+".txt", "w")

    for fname in query_files:
        q = get_query(fname)
        save_query_plan(cursor, q, fname, noisy, eps)
        exec_time = get_execution_time(cursor, q)
        f3.write(fname+", "+ str(exec_time)+" seconds\n")

    f3.close()


def probe_pg_statistic(connection, cursor):
    
    q_get_pg_stat_row='''select * from pg_statistic limit 2'''
    
    
    cursor.execute(q_get_pg_stat_row)
    output = cursor.fetchall()
    idx_lst = output[1]
    print(idx_lst[21])
    for idx2 in idx_lst:
        print(idx2)
    

    
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
        #probe_pg_statistic(connection, cursor)
        #change_pg_statistics(connection, cursor, 0.1)
         
        s = time.time()
        #change_pg_statistics(connection,cursor)
        run_queries(cursor, 0, 0)
        print("______________________________________________________________________________________\n\n")
        change_pg_statistics(connection, cursor, 0.1)
        print("______________________________________________________________________________________\n\n")
        change_pg_statistics(connection, cursor, 0.01)
        print("______________________________________________________________________________________\n\n")
        change_pg_statistics(connection, cursor, 0.001)
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

# Notes:
  # # Create the new table pg_statistics_noisy
    # create_table_query = '''
    # update pg_statistic set stanullfrac=1 
    # where starelid=1247 and staattnum=1 and stainherit = 'f';
    # '''
    
    # # Execute the query to create the new table
    # cursor.execute(create_table_query)
   
    # # Commit the transaction
    # connection.commit()
    # print("Table pg_statistics_noisy created successfully.")
    
'''
    functions to write:
    1. getStatRows(relname)
       output: row of pg_statistics for this key
    
    2. call getStatRows for list of pairs of relnames and attrnames
        and make sql query stringing the relnames with ORs
    
    3. transform statistics
        transformed = transform(copy, cols_to_change)
        
    4. update(transformed)
    '''