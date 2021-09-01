# This code is written in Python
# Prints the number of lines in a txt File 

# READ FILE 
df = open("file1.txt") 
  
# read file 
read = df.read() 
  
  
# count number of lines in the file 
line = 1
for word in read: 
    if word == '\n': 
        line += 1
print("Number of lines in file is: ", line) 
