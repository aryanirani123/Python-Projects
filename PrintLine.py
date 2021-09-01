# This code is written in Python 
# This code prints the line number next to each line in the file

FileName = "file1.txt"
f  = open(FileName,"r") 
fileContent = f.read() 
number_of_lines = 0
line_by_line = fileContent.split("\n")
number_of_lines = len(line_by_line)
print("The number of lines in the file are : ")
print(number_of_lines)

newContents = ""
lineIndex = 1
for line in line_by_line:
    newContents = newContents + "Line #" +str(lineIndex) + ": " + line + "\n"
    lineIndex=lineIndex+1


fNewFile = open("NumberedFile-" + FileName,"w")
fNewFile.write(newContents)
print("File has been created successfully")
