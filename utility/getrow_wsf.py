import psycopg2
import time
import argparse


'''
This script takes a column name and a value and returns the first primary index in pg_statistic for which the specified column has == or >= the specified value.
'''

    
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


def find_row(rtc, colname, val):
    rows_to_print = []
    num_rows_found = 0
    if colname=="correl":
        for row in rtc:
            found_correl_row = False
            offset = -1
            #print(row[0], row[1], row[2])
            for field_idx in [6, 7, 8, 9, 10]:
                if row[field_idx]==3:
                    found_correl_row = True
                    offset = field_idx - 6
                    #print(field_idx)
                    #return row[0], row[1], row[2]
            # print prim key, kind, op, col, numbers, values
            if found_correl_row:
                num_rows_found+= 1
                rows_to_print.append((row[0], row[1], row[2], row[6+offset], row[11+offset], row[16+offset], row[21+offset], row[26+offset]))
                print(row[0], row[1], row[2], row[6+offset], row[11+offset], row[16+offset], row[21+offset], row[26+offset])
                if num_rows_found == 5:
                    return rows_to_print
                found_correl_row = False

        return rows_to_print

    idx_oi = -1
    if colname =="nullfrac":
        idx_oi = 3
    elif colname == "ndist":
        idx_oi = 5
        
    for row in rtc:
        if abs(row[idx_oi]) > val:
            return row[0], row[1], row[2]

    
    
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
        parser = argparse.ArgumentParser(description='Finds a row with a specific value/range for a given column of pg_stats. For correl it currently finds a row with no correl.')
        parser.add_argument('tabname', type=str, help='Name of table to examine.')
        parser.add_argument('colname', type=str, help="Name of attribute to examine.")
        args = parser.parse_args()
        
        # Connect to the PostgreSQL database
        connection = psycopg2.connect(**db_info)
        cursor = connection.cursor() # object needed to refer to connection
       
        s = time.time()
        
        q_to_find_tbl = f'''SELECT s.*
            FROM pg_statistic s
            JOIN pg_class c ON s.starelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            JOIN pg_attribute a ON s.starelid = a.attrelid AND s.staattnum = a.attnum
            WHERE c.relname = {"'"+args.tabname+"'"}
            AND a.attname = {"'"+args.colname+"'"}
            AND n.nspname = 'public';'''
        cursor.execute(q_to_find_tbl)
        lst_rows = cursor.fetchall()
        len_row = len(lst_rows[0])
        '''for row in lst_rows:
            for i in range(len_row):
                val = row[i]
                print(i, end=", ")
                print(val)
            print("_______________________")'''
            
        lst = [0.06316666, 0.061933335, 0.0568, 0.0534, 0.051233333, 0.046066668, 0.04146667, 0.040133335, 0.031666666, 0.025666667, 0.025633333, 0.024533333, 0.0242, 0.021466667, 0.020033333, 0.018933333, 0.015333333, 0.014166667, 0.014033333, 0.012533333, 0.0104, 0.010366667, 0.0097, 0.0082, 0.0079666665, 0.0078, 0.007766667, 0.0077333334, 0.0070666666, 0.0066333334, 0.0066333334, 0.0065666665, 0.0064666667, 0.0064333333, 0.0062666666, 0.0062, 0.0061333333, 0.0061, 0.0061, 0.0060333335, 0.0058, 0.0057666665, 0.0057666665, 0.0057333335, 0.0054666665, 0.0053333333, 0.0052, 0.005133333, 0.0047, 0.004466667, 0.0042333333, 0.004033333, 0.004033333, 0.0039, 0.0038666667, 0.0038333333, 0.0038, 0.0035333333, 0.0035, 0.0034666667, 0.0031333333, 0.0028666668, 0.0027666667, 0.0026666666, 0.0024, 0.0024, 0.0023333333, 0.0020333333, 0.0020333333, 0.0020333333, 0.0018666667, 0.0016, 0.0015666666, 0.0013333333, 0.0013333333, 0.0013333333, 0.0013, 0.0013, 0.0012666667, 0.0012333334]
        print(sum(lst))
        
        lst2 = [2011,2012,2010,2009,2008,2007,2006,2005,2004,2002,2003,2013,2001,2000,1999,1998,1997,1996,1995,1994,1993,1992,1990,1991,1987,1986,1989,1988,1985,1970,1984,1978,1976,1968,1981,1971,1973,1982,1983,1979,1972,1977,1980,1974,1966,1967,1969,1975,1963,1960,1959,1961,1965,1962,1964,1958,1957,1914,1956,1955,1913,1915,1912,1954,1952,1953,1916,1910,1911,1950,1951,1917,1919,1918,1921,1930,1920,1948,1949,1937]
        lst3 = []
        for i in range(len(lst2)):
            if lst2[i] > 2010:
                lst3.append(lst[i])
        print(sum(lst3))
        '''rtc = getStatRows(cursor)
        print("Got rtcs.")
        lst_rows = find_row(rtc, args.colname.strip(), args.val)
        for lst in lst_rows:
            print(lst)'''
        lst4 = [1895,1897,1898,1900,1901,1902,1903,1904,1906,1908,1908,1909,1922,1923,1924,1925,1925,1926,1927,1928,1928,1929,1931,1932,1933,1933,1934,1935,1936,1938,1939,1939,1940,1941,1942,1943,1945,1946,1947,2014,2015]
        print(len(lst4))
        print(min(lst4))
        print(max(lst4))
        

            
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