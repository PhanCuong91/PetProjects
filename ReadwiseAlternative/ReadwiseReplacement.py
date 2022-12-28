
import requests, sqlite3, re, os, datetime, random
import subprocess as sp
token=os.environ.get('ReadwiseToken')
NUM_HIGHLIGHTS=4
def readwise_get_books_List(token, updated_days=0,from_date=None):
    querystring = {
        "category": "books",
    }
    if updated_days!=0:
        # getting books that were updated days ago
        days_ago = datetime.datetime.now() - datetime.timedelta(days=0)
        querystring['updated__gt'] = days_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
    if from_date!=None:
        # getting books that were updated from date
        querystring['updated__gt'] = from_date
    response = requests.get(
        url="https://readwise.io/api/v2/books/",
        headers={"Authorization": "Token "+token},
        params=querystring
    )
    data = response.json()
    return (data['results'])

def readwise_get_highlights_List(token, book_id=19545084,from_date=None):
    try:
        querystring = {
            "book_id": book_id,
        }
        if from_date!=None:
            # getting books that were updated from date
            querystring['updated__gt'] = from_date
        response = requests.get(
            url="https://readwise.io/api/v2/highlights/",
            headers={"Authorization": "Token "+token},
            params=querystring
        )
    except:
        raise RuntimeError("Book id is not correct. Book id: %s" % (str(r[0])))
    data = response.json()
    return(data['results'])

from dateutil import parser
def convert_utc_string_2_datetime_sql_str(s):
    dt = parser.parse(s)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def sql_comamnd_create_table(table_name='test', col_name_and_type = {'id': 'INTEGER','text': 'TEXT'}):
    # "CREATE TABLE test (book_ids INTEGER PRIMARY KEY, title TEXT, author TEXT, category TEXT, source TEXT, num_highlights INTEGER)"
    columns = ','.join( '%s %s' % (str(col),str(t)) for col,t in zip(col_name_and_type.keys(),col_name_and_type.values()))
    command = "CREATE TABLE %s (%s)" % ( table_name, columns)
    return command

def sql_command_insert(table_name='test', col_name_and_value = {'id': 123,'text': 'TEXT'}):
    # "INSERT INTO test ( book_id, title, author, category, source, num_highlights) VALUES ( 19545084 ,'The 7 Habits of Highly Effective People', 'Stephen R. Covey','books','kindle',22)"
    columns = ', '.join("'%s'" % (str(col)) for col in col_name_and_value.keys())
    values = ', '.join("'%s'"%(str(val))  for val in col_name_and_value.values())
    command = 'INSERT INTO %s ( %s ) VALUES ( %s );' % (table_name, columns, values)
    return command

def sql_command_update(table_name='test', col_name_and_value = {'id': 123,'text': 'TEXT'}, cond_col_name_and_value={'id': ['=','6']}):
    # "UPDATE table_name SET column1 = value1, column2 = value2...., columnN = valueN WHERE [condition]"
    colums_values = ', '.join("%s = '%s'" % (str(key), str(val)) for key, val in zip(col_name_and_value.keys(), col_name_and_value.values()))
    if cond_col_name_and_value == None:
        command = "UPDATE %s SET %s" % (table_name, colums_values)
    else:
        conditions = ', '.join('%s %s %s'%(str(key),str(val[0]),str(val[1])) for key, val in zip(cond_col_name_and_value.keys(), cond_col_name_and_value.values()))
        command = "UPDATE %s SET %s WHERE %s" % (table_name, colums_values, conditions)
    return command

def sql_command_order_by(table_name, sel_cols, ord_cols, cond_col_name_and_value=None,a_or_d='DESC'):
    # cond_col_name_and_value={'id': ['=','6']}
    # SELECT updated FROM highlights  WHERE book_id = 17150331 ORDER BY updated DESC;
    # SELECT column1, column2, ... FROM table_name ORDER BY column1, column2, ... ASC|DESC;
    select = ', '.join(str(col) for col in sel_cols)
    order = ', '.join(str(col) for col in ord_cols)
    if cond_col_name_and_value != None:
        conditions = ', '.join(str(key)+ ' '+ str(val[0])+' ' + str(val[1]) for key, val in zip(cond_col_name_and_value.keys(), cond_col_name_and_value.values()))
        command = "SELECT %s FROM %s WHERE %s ORDER BY %s %s" %(select, table_name,conditions ,order, a_or_d)
    else:
        command = "SELECT %s FROM %s ORDER BY %s %s" %(select, table_name, order, a_or_d)
    return command

def sql_command_search(table_name='test', col_name = ['id','text'], cond_col_name_and_value={'id': ['=','6']}):
    # 'SELECT  column1, column2,.., columnN FROM table_name WHERE [condition]'
    colums_values = ', '.join(str(key) for key in col_name)
    conditions = ', '.join(str(key)+ ' '+ str(val[0])+' ' + str(val[1]) for key, val in zip(cond_col_name_and_value.keys(), cond_col_name_and_value.values()))
    command = "SELECT %s FROM %s WHERE %s" % (colums_values, table_name, conditions)
    return command

def sql_command_table_exist(table_name='test'):
    # "SELECT count(name) FROM sqlite_master WHERE type='table' AND name='books'"
    sql="SELECT count(name) FROM sqlite_master WHERE type='table' AND name='%s'" %(table_name)
    return sql

def sql_execute(db_path="readwise/books.db", command=None):
    """
    use below code to run insert command in sqlite 
    with con:
        con.execute("command")  
    """
    if not isinstance(command,str):
        raise TypeError("command shall be string. Please check type of command parameter")

    try:
        with sqlite3.connect(db_path) as con:
            res = con.execute(command).fetchall()
            # print(res)
    except:
        raise RuntimeError("This command is not correct. Command: %s" % (command))
    # the result is list of tuple
    return res

def sql_value_preparation(dict,dict_keys=['id', 'text'], table_columns=['ids','content']):
    '''
    In case, dictionary has more keys than columns in table of database or name of keys are different with name of colums.
    This function create a new dictionary with keys are columns name and values of keys are from argumen dictionary. 
    mapping values of key id to ids, key 'text' to 'content'
    new_dict = {table_columns[0]:dict[dict_keys[0]],table_columns[1]:dict[dict_keys[1]]}
    '''
    new_dict = {}
    if len(dict_keys) != len(table_columns):
        raise KeyError("Length of 2 parameters is not equal %d != %d" % len(dict_keys),len(table_columns))
    for k1,k2 in zip(dict_keys,table_columns):
        if k1 not in dict.keys():
            raise KeyError("This key %s is not in dictonary" % k1)
        new_dict[k2] = dict[k1]
    return new_dict
	
book_table = {'table_name': 'books', 'table_columns': {'book_id': 'INTEGER','title': 'TEXT', 'author':'TEXT', 'category':'TEXT', 'source':'TEXT', 'num_highlights':'INTEGER', 'last_highlight_at':'DATETIME', 'updated':'DATETIME'}}
highlight_table={'table_name': 'highlights', 'table_columns': {'highlight_id': 'INTEGER','book_id': 'INTEGER','text': 'TEXT', 'note':'TEXT', 'location_type':'TEXT', 'highlighted_at':'DATETIME', 'updated':'DATETIME', 'reminded':'BOOLEAN' } }
con=sqlite3.connect("readwise/books.db")
table=con.execute(sql_command_table_exist('books'))
# if the count is 1, then table exists
if table.fetchone()[0]!=1: 
    sql="DROP TABLE IF EXISTS "+book_table['table_name']
    con.execute(sql)
    sql=sql_comamnd_create_table(book_table['table_name'],book_table['table_columns'])
    con.execute(sql)
    sql="DROP TABLE IF EXISTS "+highlight_table['table_name']
    con.execute(sql)
    sql=sql_comamnd_create_table(highlight_table['table_name'],highlight_table['table_columns'])
    con.execute(sql)

def synch_book_table():
    sel_cols = ['updated']
    ord_cols = ['updated']
    ret_val = {'new_book_id': [], 'existinng_book_id':[]}
    # querry book id and sort it with descended order of 'updated' column
    r = sql_execute(command=sql_command_order_by(book_table['table_name'],sel_cols, ord_cols))
    print(r)
    if len(r) == 0:
        # empty table
        res = readwise_get_books_List(token)
    else:
        # get the latest time, then get only new change from latest time
        res = readwise_get_books_List(token, from_date=r[0])
    # 2 cases: 
    # 1st: new books are added
    # 2nd: existing books are changed
    # classification: by searching book id in book table
    for r in res:
        t = sql_execute(command=sql_command_search(book_table['table_name'], ['book_id'] , {'book_id':['=', r['id']]} ))
        val =sql_value_preparation(r,['id','title','author','category','source','num_highlights','last_highlight_at','updated'],['book_id','title','author','category','source','num_highlights','last_highlight_at','updated'])
        if len(t) == 0:
            command=sql_command_insert(book_table['table_name'], val)
            ret_val['new_book_id'].append(r['id'])
        else:
            command = sql_command_update(book_table['table_name'], val , cond_col_name_and_value={'book_id':['=', r['id']]})
            ret_val['existinng_book_id'].append(r['id'])
        sql_execute(command=command)
    return ret_val
def synch_highlight_table(key, values):
    if key == 'new_book_id':
        for id in values:
            highlights= readwise_get_highlights_List(token, id)
            for h in highlights:
                # replace character U+0060 "`" to character U+2019 "’" to prevent issue in sql command
                h['text']=re.sub("'","’", h['text'])
                h['reminded'] = "FALSE"
                val=sql_value_preparation(h,['id','book_id','text','note','location_type','highlighted_at', 'updated','reminded'],['highlight_id','book_id','text','note','location_type','highlighted_at', 'updated','reminded'])
                sql=sql_command_insert(highlight_table['table_name'], val)
                sql_execute(command=sql)
    elif key == 'existinng_book_id':
        sel_cols = ['updated']
        ord_cols = ['updated']
        for id in values:
            r = sql_execute(command=sql_command_order_by(highlight_table['table_name'],sel_cols, ord_cols, cond_col_name_and_value={'book_id':['=','"%s"'%str(id)]}))
            if len(r) == 0:
                # empty table
                pass
                # res = readwise_get_highlights_List(token)
            else:
                # get the latest time, then get only new highlights which were changed from last synch
                res = readwise_get_highlights_List(token, id, from_date=r[0])
                print(res)
            # 2 cases: 
            # 1st: new highlights are added
            # 2nd: existing highlights are changed
            # classification: by searching book id in book table
            for r in res:
                t = sql_execute(command=sql_command_search(highlight_table['table_name'], ['highlight_id'] , {'highlight_id':['=', r['id']]} ))
                
                if len(t) == 0:
                    r['reminded'] = "FALSE"
                    val=sql_value_preparation(r,['id','book_id','text','note','location_type','highlighted_at', 'updated','reminded'],['highlight_id','book_id','text','note','location_type','highlighted_at', 'updated','reminded'])
                    command=sql_command_insert(highlight_table['table_name'], val)
                else:
                    val =sql_value_preparation(r,['updated'],['updated'])
                    command = sql_command_update(highlight_table['table_name'], val , cond_col_name_and_value={'highlight_id':['=', r['id']]})
                sql_execute(command=command)
res=synch_book_table()
print(res)
for key in res:
    synch_highlight_table(key,res[key])
books=sql_execute(command='SELECT title,book_id FROM books')
bs={}
for b in books:
    bs['%s'% b[1]]= b[0]
cmd = sql_command_search(table_name='highlights', col_name = ['book_id','text', 'highlight_id'], cond_col_name_and_value={'reminded': ['=', '"FALSE"']})
res = sql_execute(command=cmd)
# print(len(res))
# number of highlights need to show perday 
num_hl = NUM_HIGHLIGHTS
today=datetime.date.today()
file_name = ("readwise/"+ "%s" +".txt") % today
if os.path.exists(file_name):
    pass
else:
    # each highlight has reminded column. If highlights are shown to user via text file, then reminded column of these highlights are TRUE.
    # after all highlights were shown, then reminded column is changed to FALSE
    with open(file_name, "w",encoding='utf-8') as outfile:
        outfile.write('----------###############-----------\n')
        if len(res) > num_hl:
            # in case, highlights which are not shown to user, are more than number of highlights 
            arr = range(0, len(res), 1)
            for i in random.sample(arr,num_hl):
                # print(bs['%s' % res[i][0]])
                # print(res[i][1])

                outfile.write(bs['%s' % res[i][0]]+': \n\n')
                outfile.write(res[i][1] +'\n\n')
                outfile.write('----------###############-----------\n')
                cmd=sql_command_update(table_name='highlights', col_name_and_value={'reminded': "TRUE"}, cond_col_name_and_value={'highlight_id': ['=',res[i][2]]})
                sql_execute(command=cmd)
        else:
            # in case, highlights which are not shown to user, are less than number of highlights
            # First, get remaining highlights whose reminded column are FALSE
            for i in range(len(res)):
                # print(bs['%s' % res[i][0]])
                # print(res[i][1])
                outfile.write((bs['%s' % res[i][0]]+': \n\n'))
                outfile.write(res[i][1]+'\n\n')
                outfile.write('----------###############-----------\n')
            rem_num_hl=num_hl-len(res)
            
            # Second pick randomly highlights whose reminded column are TRUE to make sure to show number highlights as user request  
            cmd = sql_command_search(table_name='highlights', col_name = ['book_id','text', 'highlight_id'], cond_col_name_and_value={'reminded': ['=', '"TRUE"']})
            res_1 = sql_execute(command=cmd)
            arr = range(0, len(res_1), 1)
            for i in random.sample(arr,rem_num_hl):
                # print(bs['%s' % res_1[i][0]])
                # print(res_1[i][1])
                outfile.write(bs['%s' % res[i][0]]+': \n\n')
                outfile.write(res[i][1]+'\n\n')
                outfile.write('----------###############-----------\n')
                # save the highlights then change highlights's reminded column later
                res.append(res_1[i])
            # change whole rows of reminded column to FALSE
            cmd =sql_command_update(table_name='highlights', col_name_and_value={'reminded': "FALSE"}, cond_col_name_and_value=None)
            sql_execute(command=cmd)
            # Set shown highlight this time whose reminded column to TRUE
            for i in range(len(res)):
                cmd=sql_command_update(table_name='highlights', col_name_and_value={'reminded': "TRUE"}, cond_col_name_and_value={'highlight_id': ['=',res[i][2]]})
                sql_execute(command=cmd)
        programName = "notepad.exe"
        sp.Popen([programName, file_name])
