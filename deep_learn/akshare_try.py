import akshare as ak
import pandas as pd
import numpy as np
from keras import regularizers
from keras.layers import Dense,Dropout,BatchNormalization
from keras.models import Sequential, Model
from keras.callbacks import EarlyStopping
from tensorflow import random
import tensorflow as tf
import matplotlib.pyplot as plt
import matplotlib 
matplotlib.use('TkAgg')


class SPDataProcessor(object):
    def __init__(self, begin="20210101", end="20210907"):
        self.begin = begin
        self.end = end
    
    def get_df(self):
        train_x = list()
        train_y = list()
        data = ak.stock_zh_a_hist(symbol="000001", period="daily", 
                                    start_date=self.begin, 
                                    end_date=self.end, adjust="")
        data = data.drop(["日期"], axis=1)
        for i in range(0, data.shape[0]-1):
            train_x.append(data.loc[i].to_list())
        for i in range(1,data.shape[0]):
            train_y.append(data["涨跌幅"][i])
        train_x = np.array(train_x)
        train_y = np.array(train_y)
        print(data.loc[0])

        return train_x, train_y

class Model(object):

    def __init__(self, train_x, train_y):
        self.train_x = train_x
        self.train_y = train_y

    def create_model(self): 
        model = Sequential()     
        model.add(BatchNormalization())  # 输入层 批标准化 
        model.add(Dense(100,  
                        kernel_initializer='random_uniform',   # 均匀初始化
                        activation='relu',                     # relu激活函数
                        kernel_regularizer=regularizers.l1_l2(l1=0.01, l2=0.01),  # L1及L2 正则项
                        use_bias=True))   # 隐藏层
        model.add(Dropout(0.1)) # dropout法
        model.add(Dense(1,use_bias=True))  # 输出层
        model.compile(optimizer='adam',
                    loss='mse',
                    metrics=['acc'],
                    ) 

        history = model.fit(self.train_x, 
                            self.train_y, 
                            epochs=500,              # 训练迭代次数
                            batch_size=50,           # 每epoch采样的batch大小
                            validation_split=0.1,   # 从训练集再拆分验证集，作为早停的衡量指标
                            # callbacks=[EarlyStopping(monitor='val_loss', patience=20)],    #早停法
                            verbose=False,   # 不输出过程
                            )    
        model.summary()
        print("验证集最优结果：",min(history.history['val_loss']))
        acc = history.history['acc']
        val_acc = history.history['val_acc']
        loss = history.history['loss']
        val_loss = history.history['val_loss']
        epochs = range(1, len(acc) + 1)
        plt.plot(epochs, acc, 'bo', label='Training acc')
        plt.plot(epochs, val_acc, 'b', label='Validation acc')
        plt.title('Training and validation accuracy')
        plt.legend()
        plt.figure()
        plt.plot(epochs, loss, 'bo', label='Training loss')
        plt.plot(epochs, val_loss, 'b', label='Validation loss')
        plt.title('Training and validation loss')
        plt.legend()
        plt.show()

if __name__ == "__main__":
    SPData = SPDataProcessor()
    train_x, train_y = SPData.get_df()
    Model(train_x, train_y).create_model()
