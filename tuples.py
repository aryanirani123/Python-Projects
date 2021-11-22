#Empty tuple 
new_tuple = ()
print(new_tuple)

#Tuple with numbers
num_tuple = (1,2,3,4,5)
print(num_tuple)

#Tuple with strings and numbers
mixed_tuples = (1,"Hello",908,9.988)
print(mixed_tuples)

#List inside a tuple - Nested Tuples

list_tuples = (1,2,3,[1,231,2])
print(list_tuples)

#Create a tuple with only on element

element_tuple = ("Hello",)
print(element_tuple)



#packing and unpacking tuples

my_tuple = 1,2,3,"Hello","Wassup"

a,b,c,d,e = my_tuple

print(a)
print(b)
print(c)
print(d)
print(e)


#Accessing elements of tuple

#Three ways to access elements of a tuple 
# Indexing
# Negative Indexing 
# Slicing



name_tuple = ('a','r','y','a','n')
#get the second element from the tuple
print(name_tuple[1])   # 'r'
#get the last element of the tuple
print(name_tuple[4])   # 'n'
#Get elements from nested tuple
nested_tuple = ("Hello",[1,234,"Yes"],'No')

#Index of each element in the tuple
#  Hello      1      234      "Yes"    'No'
#    0      [1][0]  [1][1]    [1][2]   [2]

#get 'Yes' from the tuple
print(nested_tuple[2])

# NEGATIVE INDEXING

neg_tuple = ('a','b','c','d','e')
#    a   b   c   d   e
#   -5  -4  -3  -2  -1

#get the second element of the tuple
print(neg_tuple[-4])

#get the last element of the tuple 
print(neg_tuple[-1])


# SLICING

my_tuple = ('a','b','c','d','e')
#print elements b c d 
print(my_tuple[1:4])


# Make changes to a Tuple
# you cannot make changes to tuples since they are immutable
#og_tuple = (1,2,3,4,5)
#og_tuple[1] = 3
#print(og_tuple)

# But if you can make changes to nested tuples
my_tuple1 = (1,22,3,[2,34])
#want to replace 2 with 56
my_tuple1[3][0] = 56
print(my_tuple1)


#Tuples cannot be changed but can be reassigned

# print all the elements of a tuple

name_tuple = ("Aryan","Neil","Dev","Rohan")

for name in name_tuple:
    print(name)

#Check if element is present in tuple

name_tuple = ("Aryan","Neil","Dev","Rohan")
#Check if Aryan is present in the tuple
print("Aryan" in name_tuple)

#check if x is present in the tuple
print("x" in name_tuple)
