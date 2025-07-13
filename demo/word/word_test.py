from mailmerge import MailMerge
import datetime
 
template = "From.docx"
document = MailMerge(template)
 
print(document.get_merge_fields())

document.merge(
    From='123456dadeng@qq.com'
)

#输出的docx文件
document.write('output.docx')