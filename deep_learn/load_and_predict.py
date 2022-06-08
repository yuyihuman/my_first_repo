# from distutils.command.build_scripts import first_line_re
from keras.datasets import boston_housing #导入波士顿房价数据集
from keras.models import load_model
import numpy as np
import matplotlib.pyplot as plt
import matplotlib 
matplotlib.use('TkAgg')

(train_x, train_y), (test_x, test_y) = boston_housing.load_data()

model = load_model('my_first_model.h5')
model.summary()   #打印模型概述信息

# 测试集预测结果
pred_y = model.predict(test_x)[:,0]

print("正确标签：",test_y)
print("模型预测：",np.round(pred_y,1))
print("==============================================================")