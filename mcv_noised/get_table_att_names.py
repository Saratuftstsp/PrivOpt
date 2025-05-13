import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML

def is_subselect(parsed):
    return parsed.is_group and any(token.ttype is DML and token.value.upper() == 'SELECT' for token in parsed.tokens)

def extract_tables(parsed):
    tables = set()
    for item in parsed.tokens:
        if isinstance(item, IdentifierList):
            for identifier in item.get_identifiers():
                tables.add(identifier.get_real_name())
        elif isinstance(item, Identifier):
            tables.add(item.get_real_name())
    return tables

def extract_columns(parsed):
    columns = set()
    for item in parsed.tokens:
        if isinstance(item, IdentifierList):
            for identifier in item.get_identifiers():
                columns.add(identifier.get_real_name())
        elif isinstance(item, Identifier):
            columns.add(item.get_real_name())
    return columns

def parse_sql(query):
    parsed = sqlparse.parse(query)[0]
    print(parsed)    
    tables = set()
    columns = set()
    from_seen = False

    for token in parsed.tokens:
        if token.ttype is Keyword and token.value.upper() == 'FROM':
            from_seen = True
        elif from_seen and isinstance(token, IdentifierList):
            tables.update(extract_tables(token))
        elif from_seen and isinstance(token, Identifier):
            tables.add(token.get_real_name())
        elif isinstance(token, IdentifierList) or isinstance(token, Identifier):
            columns.update(extract_columns(token))
    
    #print("Tables:", tables)
    #print("Columns:", columns)
    
    return tables, columns
    
def get_query(fname):
    query_files_dir = "/Users/saraalam/Desktop/PrivOptCode/job/"
    f = open(query_files_dir+fname+".sql", "r")
    q = ""
    for _ in f.readlines():
        q+= _.strip()+" "
    f.close()
    return q

def main():
    queries = ["6a", "13a", "16d", "17b", "25c", "17c", "28a", "26a", "27c", "19d"]
    q_dict = {}
    for fname in queries:
        q = get_query(fname)
        q_dict[fname] = q
    
    all_tables = set()
    for q in q_dict:
        tables, columns = parse_sql(q_dict[q])
        for t in tables:
            all_tables.add(t)

        
        #print()
    print(all_tables)

if __name__=='__main__':
    main()

