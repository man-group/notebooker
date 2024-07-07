# + {"tags": ["parameters"]}
x_n = 2000
y_n = 2070
# -

filename = 'hello.txt'

# Open the file and read its content
with open(filename, 'r') as file:
    content = file.read()

# Print the content
print(content)