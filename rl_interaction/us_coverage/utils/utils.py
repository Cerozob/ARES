import re

def read_file_number_of_methods(file):
    pattern = re.compile("\"[0-9]+\":{")
    text = file.read()
    lista = re.findall(pattern,text)
    string_number = lista[-1].replace("\"","").replace(":","").replace("{","")
    return int(string_number)
    
    
    
        