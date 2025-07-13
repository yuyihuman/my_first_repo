#!/usr/bin/python
# -*- coding: UTF-8 -*-
 
from xml.dom.minidom import parse
import xml.dom.minidom
 
# 使用minidom解析器打开 XML 文档
DOMTree = xml.dom.minidom.parse("SimOutput_20210827_144649.xml")
collection = DOMTree.documentElement
# if collection.hasAttribute("shelf"):
#    print ("Root element : %s" % collection.getAttribute("shelf"))
 
# 在集合中获取所有电影
TestRuns = collection.getElementsByTagName("TestRun")
 
# 打印每部电影的详细信息
for TestRun in TestRuns:
   print ("*****TestRun*****")
   # if TestRun.hasAttribute("title"):
   #    print ("Title: %s" % TestRun.getAttribute("title"))
 
   FilePath = TestRun.getElementsByTagName('FilePath')[0]
   print ("FilePath: %s" % FilePath.childNodes[0].data)

   Variations = TestRun.getElementsByTagName("Variation")
   for Variation in Variations:
      print ("*****Variation*****")
      Name = Variation.getElementsByTagName('Name')[0]
      print ("Name: %s" % Name.childNodes[0].data)
      Result = Variation.getElementsByTagName('Result')[0]
      # print ("Result: %s" % Result.childNodes[0].nodeValue)
      if Result.firstChild:
         print ("Result:{}".format(Result.firstChild.data))
      else:
         print ("Result: None",end="\n\n")


   # format = TestRun.getElementsByTagName('format')[0]
   # print ("Format: %s" % format.childNodes[0].data)
   # rating = TestRun.getElementsByTagName('rating')[0]
   # print ("Rating: %s" % rating.childNodes[0].data)
   # description = TestRun.getElementsByTagName('description')[0]
   # print ("Description: %s" % description.childNodes[0].data)