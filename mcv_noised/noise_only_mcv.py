import psycopg2
import time
import numpy as np
import matplotlib.pyplot as plt

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
            
            
def get_new_mcv_mcf(relid, attnum):
    vals_and_counts = get_col_counts(relid, attnum)
    

def get_col_counts(relid, attnum, cursor):
    q1 = f'''select c.relname from pg_class c join pg_statistic s on c.oid=s.starelid where s.starelid={relid} limit 1'''
    cursor.execute(q1)
    tablename = cursor.fetchall()[0][0]
    print(tablename)
    q2 = f'''select a.attname from pg_class c join pg_attribute a on c.oid=a.attrelid where a.attrelid={relid} and a.attnum={attnum}'''
    cursor.execute(q2)
    attname = cursor.fetchall()[0][0]
    print(attname)
    
    q = f'''select {attname}, count(*) c from {tablename} group by {attname} order by c desc'''
    
    cursor.execute(q)
    
    vals_and_counts = cursor.fetchall()
    vals, counts = clean_vals_and_counts(vals_and_counts)

    
    return vals, counts

def clean_vals_and_counts(vals_and_counts):
    num_rows = len(vals_and_counts)
    vals = []
    counts = []
    for i in range(num_rows):
        row = vals_and_counts[i]
        val = row[0]
        if val!= None:
            vals.append(val)
            counts.append(float(row[1]))
    return vals, counts
    

# Want to mask histogram
# so if we find a stakind that is 1 
# must noise FOUR indexes:     1) the index of this stakind
#                              2) index v + k 
#                                   where k = Offset of this stakind from start of stakind indexes i.e 6
#                                   and v = start of the stavalues indexes i.e 26
#                              3) index n + k
#                                   where k = Offset of this stakind from start of stakind indexes i.e 6
#                                   and n = start of the stanumbers indexes i.e 21
#                              4) index o + k
#                                   where k = Offset of this stakind from start of stakind indexes i.e 6
#                                   and o = start of the staops indexes i.e 11
#                              5) index c + k
#                                   where k = Offset of this stakind from start of stakind indexes i.e 6
#                                   and c = start of the stacols indexes i.e 16

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

def strify(new_vals, new_counts):
    new_vals_str, new_counts_str = "{", "{"
    for i in range(10):
        new_vals_str += new_vals[i]
        new_counts_str += str(new_counts[i])
        if i != 9:
            new_vals_str+=","
            new_counts_str+=","
        new_vals_str+="}"
        new_counts_str+="}"
    return new_vals_str, new_counts_str

def insert_mask_into_rtc(rtc,offsets):
    changed_rtc = []
    row_len = len(rtc[0])
    for row_idx in range(len(rtc)):
        row = rtc[row_idx]
        new_row = (row[0], row[1], row[2])
        offset = offsets[row_idx] # gets changes to offset of the stakind from start of stakind if one of the stakind is found to be 1
        new_vals, new_counts = None, None
        if offset!=-1:
            clean_vals, clean_counts = clean_vals_and_counts(row[26+offset], row[21+offset])
            new_counts = add_laplace_noise(clean_counts, 0.1)
            new_vals, new_counts = get_top_ten(clean_vals, clean_counts)
            new_vals_str, new_counts_str = strify(new_vals, new_counts)
        #1. stakinds
        for field_idx in range(3, row_len):            
            if 6<= field_idx <= 10:
                val = row[field_idx]
                if val == 1 and offset==-1:
                    # we have found stakind that says there IS a non-null mcv and mcf list
                    offset = field_idx - 6

                new_row = new_row + (val,) # either way, we do not change the stakind
                    
            #2. stavalues
            elif 26<= field_idx <= 30:
                val = row[field_idx]
                if offset > -1 and field_idx == 26 + offset:
                    # we have found stakind that says there IS a non-null mcv and mcf list
                    # and this is the right offset away from the start of stavalues
                    new_row = new_row + (new_vals_str,)
                else:
                    new_row = new_row + (val,) # otherwise we do not mask it with None
                    
            #3. stanumbers
            elif 21 <= field_idx <= 25:
                val = row[field_idx]
                if offset > -1 and field_idx == 21 + offset:
                    # we have found stakind that says there IS a non-null mcv and mcf list
                    # and this is the right offset away from the start of stanumbers
                    #new_val, new_counts = get_new_mcv_mcf(row[0], row[1])
                    new_row = new_row + (new_counts_str,)
                else:
                    new_row = new_row + (val,) # otherwise we do not mask it with None
                    
            #4. staops
            elif 11<= field_idx <= 15:
                val = row[field_idx]
                if offset > -1 and field_idx == 11 + offset:
                    # we have found stakind that says there IS a non-null mcv and mcf list
                    # and this is the right offset away from the start of staops
                    pass
                new_row = new_row + (val,) # otherwise we do not mask it with 0
                    
            #5. stacols
            elif 16<= field_idx <= 20:
                val = row[field_idx]
                if offset > -1 and field_idx == 16 + offset:
                    # we have found stakind that says there IS a non-null mcv and mcf list
                    # and this is the right offset away from the start of stacols
                    pass
                new_row = new_row + (val,) # otherwise we do not mask it with 0
                    
            # nullfrac, stawidth, ndist mask 0
            else:
                val = row[field_idx]
                new_row = new_row + (val,)

        changed_rtc.append(new_row)
    return changed_rtc


    
def insert_cr_into_pg_statistic(cr, connection, cursor, offsets_per_row):
    col_names = ["stanullfrac", "stawidth", "stadistinct", "stakind1", "stakind2","stakind3", "stakind4", "stakind5", "staop1", "staop2", "staop3", "staop4", "staop5", "stacoll1", "stacoll2", "stacoll3", "stacoll4", "stacoll5", "stanumbers1", "stanumbers2", "stanumbers3", "stanumbers4", "stanumbers5", "stavalues1", "stavalues2", "stavalues3", "stavalues4", "stavalues5"]
    for row_idx in range(len(cr)):
        offset = offsets_per_row[row_idx]
        for j in range(3, 31):
            if offset!=-1 and (j==6+offset or j==11+offset or j==15+offset or j==21+offset or j==26+offset):
                '''relid = cr[row_idx][0]
                attnum = cr[row_idx][1]
                inh = cr[row_idx][2]
                print(f"Row: {row_idx}, Col: {j}, Relid: {relid}, Attnum: {attnum}, Inh: {inh}, Offset: {offset}")'''
                field_val = cr[row_idx][j]
                if field_val == None:
                    q = """
                        UPDATE pg_statistic
                        SET """ + col_names[j-3] + """ = %s
                        WHERE starelid = %s
                        and staattnum = %s
                        and stainherit = %s
                    """
                    cursor.execute(q, (None, cr[row_idx][0], cr[row_idx][1], cr[row_idx][2]))  
                else:
                    q = '''
                    update pg_statistic set {}={} where starelid={} and staattnum={} and stainherit={};
                    '''.format(col_names[j-3], field_val, cr[row_idx][0], cr[row_idx][1], cr[row_idx][2])
                    cursor.execute(q)
            
                # Commit the transaction
                connection.commit()
        

    
def get_orig_vals(rtc, col_idx):
    orig_vals = []
    r_idx = 0
    for r in rtc:
        orig_vals.append(rtc[r_idx][col_idx])
        r_idx+=1
    return orig_vals



def probe_pg_statistic(cursor):
    
    q_get_pg_stat_row='''select * from pg_statistic limit 5'''
    
    
    cursor.execute(q_get_pg_stat_row)
    output = cursor.fetchall()
    row = output[1]
    for i in range(len(row)):
        field = row[i]
        print(f"Index {i}: {field}")
        
    return row[0], row[1], row[2]
        
def get_specific_row(relid, attnum, inh, cursor):
    q_get_pg_stat_row='''select * from pg_statistic where starelid={} and staattnum={} and stainherit={};'''.format(relid, attnum, inh)
    
    
    cursor.execute(q_get_pg_stat_row)
    output = cursor.fetchall()
    row = output[0]
    for i in range(len(row)):
        field = row[i]
        print(f"Index {i}: {field}")
    
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


def plot_top_ten(top_ten_vals, top_ten_counts, plot_filename):
    
    
    # Create the plot
    plt.figure(figsize=(15, 5))
    plt.bar(top_ten_vals, top_ten_counts, color='blue')

    plt.title('Most common values and counts example')
    plt.xlabel('Most Common Values')
    plt.ylabel('Most Common Frequencies')
    plt.legend()
    plt.grid()


    # Save the plot

    plt.savefig(plot_filename)

    # Show the plot (optional)
    #plt.show()

    print(f'Plot saved to {plot_filename}')
    
def get_top_ten(vals, counts):

    num_vals = len(vals)
    count_dict = {}
    for i in range(num_vals):
        val = vals[i]
        count = counts[i]
        if count not in count_dict:
            count_dict[count]= []
            
        count_dict[count].append(val)
        
        
    counts.sort()
    

    top_ten_vals, top_ten_counts = [], []
    for i in range(1, 21):
        count = counts[-i]
        count_vals = count_dict[count]
        for j in range(len(count_vals)):
            val = count_vals[j]
            top_ten_vals.append(val)
            top_ten_counts.append(count)
            if len(top_ten_vals) >= 20:
                break
        if len(top_ten_vals) >= 20:
                break
            
    other_count = 0
    for i in range(num_vals):
        val = vals[i]
        count = counts[i]
        if val not in top_ten_vals:
            other_count += count
            
    '''top_ten_vals.append("Other")
    top_ten_counts.append(other_count)'''
    
    print(top_ten_vals)
    
    return top_ten_vals, top_ten_counts
    
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
        
        #cursor.execute("analyze")
        
        #1.
        # Get rows of pg_statistic that we want to change
        # i.e rows that belong to the namespace 'public'
        # these are the user-created table's stat rows
        # rtc == rows to change
        vals, counts = get_col_counts(16428, 7, cursor)
        top_ten_vals, top_ten_counts = get_top_ten(vals, counts)
        plot_top_ten(top_ten_vals,top_ten_counts,"orig_counts")
        noisy_counts = add_laplace_noise(counts, 0.1)
        top_ten_vals_after_noise, noisy_top_ten_counts = get_top_ten(vals, noisy_counts)
        plot_top_ten(top_ten_vals_after_noise, noisy_top_ten_counts, "noisy_counts")

        '''relid, attnum, inh = probe_pg_statistic(cursor)
        print("Before: ")
        get_specific_row(30082, 8, False, cursor)
        print("________________________________\n")'''
        
        '''rtc = getStatRows(cursor)
        print("Got rtcs.")
        offsets_per_row = find_offsets(rtc) #
        spec_row_idx = -1
        for i in range(len(offsets_per_row)):
            if offsets_per_row[i] != -1:
                spec_row_idx = i
                break
        print("found offsets")
        cr = insert_mask_into_rtc([rtc[spec_row_idx]], offsets_per_row)
        print("Changed rows.")'''
        '''insert_cr_into_pg_statistic(cr, connection, cursor, offsets_per_row)
        print("Put changed rows into pg_statistic.")
        
        print("\n________________________________")
        print("After: ")
        get_specific_row(30082, 8, False, cursor)
        print("________________________________\n")'''
            
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