import re

a="1234567"
b=re.sub("123","",a)
print("{}".format(b))