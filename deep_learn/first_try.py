# from distutils.command.build_scripts import first_line_re
from keras.datasets import boston_housing #导入波士顿房价数据集
from keras import regularizers
from keras.layers import Dense,Dropout,BatchNormalization
from keras.models import Sequential, Model
from keras.callbacks import EarlyStopping

import pandas as pd 
import pandas_profiling
from pandas_profiling import profile_report

import numpy as np

import time

from tensorflow import random
import tensorflow as tf
# from sklearn.metrics import mean_squared_error

import matplotlib.pyplot as plt
import matplotlib 
matplotlib.use('TkAgg')

(train_x, train_y), (test_x, test_y) = boston_housing.load_data()
# print(train_x[0])

#  特征名称
feature_name = ['CRIM|住房所在城镇的人均犯罪率',
 'ZN|住房用地超过 25000 平方尺的比例',
 'INDUS|住房所在城镇非零售商用土地的比例',
 'CHAS|有关查理斯河的虚拟变量(如果住房位于河边则为1,否则为0)',
 'NOX|一氧化氮浓度',
 'RM|每处住房的平均房间数',
 'AGE|建于 1940 年之前的业主自住房比例',
 'DIS|住房距离波士顿五大中心区域的加权距离',
 'RAD|距离住房最近的公路入口编号',
 'TAX 每 10000 美元的全额财产税金额',
 'PTRATIO|住房所在城镇的师生比例',
 'B|1000(Bk|0.63)^2,其中 Bk 指代城镇中黑人的比例',
 'LSTAT|弱势群体人口所占比例']

train_df = pd.DataFrame(train_x, columns=feature_name)  # 转为df格式
# print(train_df.loc[0])
# profile = pandas_profiling.ProfileReport(train_df) 
# profile.to_file(output_file= "Titanic data profiling.html")
# pandas_profiling.ProfileReport(train_df) 

np.random.seed(1) # 固定随机种子，使每次运行结果固定
random.set_seed(1)


# 创建模型结构：输入层的特征维数为13；1层k个神经元的relu隐藏层；线性的输出层；

for k in [100]:  # 网格搜索超参数：神经元数k
    
    model = Sequential()

    model.add(BatchNormalization())  # 输入层 批标准化 

    model.add(Dense(k,  
                    kernel_initializer='random_uniform',   # 均匀初始化
                    activation='relu',                     # relu激活函数
                    kernel_regularizer=regularizers.l1_l2(l1=0.01, l2=0.01),  # L1及L2 正则项
                    use_bias=True))   # 隐藏层

    model.add(Dropout(0.1)) # dropout法

    model.add(Dense(1,use_bias=True))  # 输出层

    model.compile(optimizer='adam', loss='mse') 

    # 训练模型
    start = time.time()
    history = model.fit(train_x, 
                        train_y, 
                        epochs=500,              # 训练迭代次数
                        batch_size=50,           # 每epoch采样的batch大小
                        validation_split=0.1,   # 从训练集再拆分验证集，作为早停的衡量指标
                        callbacks=[EarlyStopping(monitor='val_loss', patience=20)],    #早停法
                        verbose=False)  # 不输出过程  

    end = time.time()
    print("训练时间：{}".format(end-start))
    print("验证集最优结果：",min(history.history['val_loss']))
    model.summary()   #打印模型概述信息
    # 模型评估：拟合效果
    plt.plot(history.history['loss'],c='blue')    # 蓝色线训练集损失
    plt.plot(history.history['val_loss'],c='red') # 红色线验证集损失
    plt.show()

    # 模型评估：测试集预测结果
    pred_y = model.predict(test_x)[:,0]

    print("正确标签：",test_y)
    print("模型预测：",pred_y )

    mse = tf.losses.mean_squared_error(test_y, pred_y)
    print("实际与预测值的差异：",mse)
    print("==============================================================")

    #绘图表示

    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False

    # 设置图形大小
    plt.figure(figsize=(8, 4), dpi=80)
    plt.plot(range(len(test_y)), test_y, ls='-.',lw=2,c='r',label='真实值')
    plt.plot(range(len(pred_y)), pred_y, ls='-',lw=2,c='b',label='预测值')

    # 绘制网格
    plt.grid(alpha=0.4, linestyle=':')
    plt.legend()
    plt.xlabel('number') #设置x轴的标签文本
    plt.ylabel('房价') #设置y轴的标签文本

    # 展示
    plt.show()

    # 保存模型
    model.save('my_first_model.h5')