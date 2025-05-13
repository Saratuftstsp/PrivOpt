import psycopg2
import time
import argparse
import numpy as np

'''
This script takes erases all non-public fields of pg_statistic.
"Erase" means the true values are replaced with default values.
Run this before running queries, to get oblivious (i.e no system catalog) runtimes.
'''

def insert_mask_into_rtc(rtc):
    # set everything except principle key values to defaults from documentation
    # reuse code for noising using second parameter
    changed_rtc = []
    row_len = len(rtc[0])
    for row_idx in range(len(rtc)):
        new_row = tuple()
        for field_idx in range(row_len):
            if (field_idx in [3,5]) or (6 <= field_idx <= 20):
                new_row = new_row + (0,) # mask for nullfrac 0
                                        # mask for kind, op and col 0
                    
            elif 21<= field_idx <= 30:
                new_row = new_row + (None,)
                
            else:
                new_row = new_row + (rtc[row_idx][field_idx],) # default value for stawidth is 0, but do not mask because this is public information
                                                                # and prim key fields
                
        changed_rtc.append(new_row)
    return changed_rtc


def insert_cr_into_pg_statistic(cr, connection, cursor):
    col_names = ["stanullfrac", "stawidth", "stadistinct", "stakind1", "stakind2","stakind3", "stakind4", "stakind5", "staop1", "staop2", "staop3", "staop4", "staop5", "stacoll1", "stacoll2", "stacoll3", "stacoll4", "stacoll5", "stanumbers1", "stanumbers2", "stanumbers3", "stanumbers4", "stanumbers5", "stavalues1", "stavalues2", "stavalues3", "stavalues4", "stavalues5"]
    for row_idx in range(len(cr)):
        for j in range(3, 31): # wew're doing this for indexes 3 through to 30 of the rows
            field_val = cr[row_idx][j]
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
            # Commit the transaction(s)
            connection.commit()
        

    
def get_orig_vals(rtc, col_idx):
    orig_vals = []
    r_idx = 0
    for r in rtc:
        orig_vals.append(rtc[r_idx][col_idx])
        r_idx+=1
    return orig_vals
        

    
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
    (select c.oid as starelid from pg_class c join pg_namespace n on c.relnamespace=n.oid)
    '''
    
    # Execute the query to create the new table
    cursor.execute(copy_public_namespace_stat_query)
        

    #print("Rels from namespace == public fetched successfully.\n\n")
    
    return cursor.fetchall()


# function(s) for debugging
def probe_pg_statistic(cursor):
    # getting some primary id to see the structure/typical values of a row
    '''relid, attnum, inh = sample_pg_statistic(cursor)'''
    
    # getting the names of the columns with their index number for future reference
    '''print_pg_statistic_col_names()'''
    
    # getting a row where all stavalues and all stanumbers are null
    rtc = getStatRows(cursor)
    prim_key = find_all_sta_vals_null_row(rtc)
    if prim_key!= None:
        print_specific_row(int(prim_key[0]), prim_key[1], prim_key[2], cursor)
    
def sample_pg_statistic(cursor):
    
    q_get_pg_stat_row='''select * from pg_statistic limit 5'''
    
    
    cursor.execute(q_get_pg_stat_row)
    output = cursor.fetchall()
    row = output[1]
    for i in range(len(row)):
        field = row[i]
        print(f"Index {i}: {field}")
        
    return row[0], row[1], row[2]


def print_specific_row(relid, attnum, inh, cursor):
    '''
    Given a relation ID, an attribute no., and inherited boolean and a cursor to a db
    Print the row from pg_statistic for this relation, attribute and inherited triple
    '''
    q_get_pg_stat_row='''select * from pg_statistic where starelid={} and staattnum={} and stainherit={};'''.format(relid, attnum, inh)
    
    cursor.execute(q_get_pg_stat_row)
    output = cursor.fetchall()
    row = output[0]
    #print(f"Length of pg_statistic row: {len(row)}")
    for i in range(len(row)):
        field = row[i]
        print(f"Index {i}: {field}")
        
def print_pg_statistic_col_names():
    col_names = [ "starelid", "staattnum", "stainherit" ,"stanullfrac", "stawidth", "stadistinct", "stakind1", "stakind2","stakind3", 
                 "stakind4", "stakind5", "staop1", "staop2", "staop3", "staop4", "staop5", 
                 "stacoll1", "stacoll2", "stacoll3", "stacoll4", "stacoll5", "stanumbers1", 
                 "stanumbers2", "stanumbers3", "stanumbers4", "stanumbers5", "stavalues1", 
                 "stavalues2", "stavalues3", "stavalues4", "stavalues5"]
    for i in range(len(col_names)):
        print(f"Index {i} is {col_names[i]}")
        
def find_all_sta_vals_null_row(rtc):
    row_idx = 0
    num_rows = len(rtc)
    row = None
    stop1 = False
    stop2 = False
    while (row_idx < num_rows) and (not stop1) and (not stop2):
        row = rtc[row_idx]
        stop1 = all_sta_nums_null(row)
        stop2 = all_sta_vals_null(row)
        if stop1:
            if stop2:
                return row[0:3]
        row_idx += 1
        
    return None
        
def all_sta_vals_null(row):
    if row==None:
        return False
    stavals1 = row[26]
    stavals2 = row[27]
    stavals3 = row[28]
    stavals4 = row[29]
    stavals5 = row[30]
    return (stavals1 == None) and (stavals2 == None) and (stavals3 == None) and (stavals4 == None) and (stavals5 == None)

def all_sta_nums_null(row):
    if row==None:
        return False
    stanums1 = row[21]
    stanums2 = row[22]
    stanums3 = row[23]
    stanums4 = row[24]
    stanums5 = row[25]
    return (stanums1 == None) and (stanums2 == None) and (stanums3 == None) and (stanums4 == None) and (stanums5 == None)
        
    
    
def main():
    # Database connection parameters
    db_info = {
        'dbname': 'imdb',
        'user': 'saraalam',
        'password': 'papp17',
        'host': 'localhost',
        'port': '5432'
    }
    
    try:
        #parser = argparse.ArgumentParser(description='Mask columns in pg_statistic.')
        #parser.add_argument('noised_cols', type=str, help='Name(s) of column(s) to not mask since it will be noised. Comma-separated. Enter random string if nothing is noised/everything needs to be masked/hidden.')
        #args = parser.parse_args()
        
        # Connect to the PostgreSQL database
        connection = psycopg2.connect(**db_info)
        cursor = connection.cursor() # object needed to refer to connection

        
        s = time.time()
        
        #0. debug/sanity check
        #probe_pg_statistic(cursor)
        
        #1.
        # Get rows of pg_statistic that we want to change
        # i.e rows that belong to the namespace 'public'
        # these are the user-created table's stat rows
        # rtc == rows to change
        
        #sample_pg_statistic(cursor)
        print("Before: ")
        print_specific_row(16465, 5, False, cursor)
        print("\n\n______________________________________________________\n\n")
        print_specific_row(1260, 11, False, cursor)

        
        print("________________________________")
        
        rtc = getStatRows(cursor)
        print("Got rtcs.")
        #noised_col_lst = args.noised_cols.strip().split(",")
        cr = insert_mask_into_rtc(rtc)
        print("Changed rows.")
        insert_cr_into_pg_statistic(cr, connection, cursor)
        print("Put changed rows into pg_statistic.")
        
        print("________________________________")
        print("After: ")
        print_specific_row(16465, 5, False, cursor)
        print("\n\n______________________________________________________\n\n")
        print_specific_row(1260, 11, False, cursor)
            
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