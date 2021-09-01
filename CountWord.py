# This code is written in Python
# This code reads the content of a file and prints the count of each word

text = open("file1.txt", "r") 
  
d = dict() 
  
for line in text: 
    line = line.strip() 
    line = line.lower()  
    words = line.split(" ") 
  
    for word in words: 
        if word in d: 
            
            d[word] = d[word] + 1
        else: 
           
            d[word] = 1
  
 
for key in list(d.keys()): 
    print(key, ":", d[key]) 
