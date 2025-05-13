import argparse
import psycopg2

def get_pgs_key(table_name, cursor):
    query = ' SELECT s.starelid as relid, s.staattnum as attnum, s.stainherit AS inherited FROM pg_statistic s JOIN pg_class c ON c.oid = s.starelid JOIN pg_attribute a ON c.oid = a.attrelid AND a.attnum = s.staattnum LEFT JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname=\''+table_name+'\''
    cursor.execute(query)
    return cursor.fetchall()

def get_pgs_rows(pgs_keys, cursor):
    rows = []
    for k in pgs_keys:
        pgs_row = (get_specific_row(k[0], k[1], k[2], cursor))
        rows.append(pgs_row)
    return rows
    
def get_specific_row(relid, attnum, inh, cursor):
    q_get_pg_stat_row='''select * from pg_statistic where starelid={} and staattnum={} and stainherit={};'''.format(relid, attnum, inh)
    
    
    cursor.execute(q_get_pg_stat_row)

    '''row = cursor.fetchall()[0]
    for i in range(len(row)):
        field = row[i]
        print(f"Index {i}: {field}")'''
    return cursor.fetchall()[0]

def find_offsets(rtc):
    offsets_per_row = []
    for row_idx in range(len(rtc)):
        row = rtc[row_idx]
        offset = -1 # gets changes to offset of the stakind from start of stakind if one of the stakind is found to be 1
        #1. stakinds
        for field_idx in range(6, 11):            
            if 6<= field_idx <= 10:
                val = row[field_idx]
                if val == 1 and offset==-1: # stakindn = 1 ---> mcfs and mcvs exist
                    # we have found stakind that says there IS a non-null mcv and mcf list
                    offset = field_idx - 6
        offsets_per_row.append(offset)
    return offsets_per_row

def get_table_and_att_names(lst, cursor):
    tabs_and_atts = []
    for row in lst:
        relid = row[0]
        attnum = row[1]
        inh = row[2]
        query = '''  SELECT c.relname as tablename, a.attname as attname FROM pg_statistic s JOIN pg_class c ON c.oid = s.starelid JOIN pg_attribute a ON c.oid = a.attrelid 
        AND a.attnum = s.staattnum LEFT JOIN pg_namespace n ON n.oid = c.relnamespace WHERE starelid={} and staattnum={} and stainherit={};
        '''.format(relid, attnum, inh)
        cursor.execute(query)
        tabs_and_atts.append(cursor.fetchall()[0])
    return tabs_and_atts

def print_mcv_att_names(rows, offsets, cursor, isdigit=1):
    lst_nums = []
    lst_strs = []
    
    for i in range(len(rows)):
        row = rows[i]
        offset = offsets[i]
        mcv = row[26+offset].strip("\{\}").split(",")
        if mcv[0].isdigit(): 
            lst_nums.append(row)
        else: 
            lst_strs.append(row)
            
    to_print = []
    if isdigit==1:
        to_print = get_table_and_att_names(lst_nums, cursor)
    else:
        to_print = get_table_and_att_names(lst_strs, cursor)
        
    '''for p in to_print:
        print(p)'''
        
    return to_print

def print_q_form(lst):
    for t in lst:
        tab = t[0]
        att = t[1]
        q = ''' select {} from {}'''.format(att, tab)
        print(q)
        
    

def main():
    # Database connection parameters
    db_info = {
        'dbname': 'imdb',
        'user': 'postgres',
        'password': '1908',
        'host': 'localhost',
        'port': '5433'
    }
    
    # Connect to the PostgreSQL database
    connection = psycopg2.connect(**db_info)
    cursor = connection.cursor() # object needed to refer to connection
        
    # get pg_statistics primary keys associated with given tables names
    pgs_keys = []
    tables = {'comp_cast_type', 'company_type', 'movie_info', 'char_name', 'keyword', 'kind_type', 'movie_info_idx', 'movie_keyword', 'complete_cast', 'company_name', 'movie_link', 'name', 'aka_name', 'role_type', 'movie_companies', 'link_type', 'title', 'info_type', 'cast_info'}
    
    for t in tables:
        
        pgs_key = get_pgs_key(t, cursor)
        for k in pgs_key:
            pgs_keys.append(k)
            

    # use the primary keys to get the rows from pg_statistics
    pgs_rows = get_pgs_rows(pgs_keys, cursor)
    # check which rows have mcvs
    offsets_per_row = find_offsets(pgs_rows)
    rows_with_mcvs = []
    offsets_for_rows_with_mcvs = []
    for i in range(len(offsets_per_row)):
        offset = offsets_per_row[i]
        if offset!=-1:
            rows_with_mcvs.append(pgs_rows[i])
            offsets_for_rows_with_mcvs.append(offset)
            
    
    '''to_print_num = print_mcv_att_names(rows_with_mcvs, offsets_for_rows_with_mcvs, cursor)
    print_q_form(to_print_num)'''
    to_print_str = print_mcv_att_names(rows_with_mcvs, offsets_for_rows_with_mcvs, cursor, 0)
    print_q_form(to_print_str)
        
if __name__=='__main__':
    main()