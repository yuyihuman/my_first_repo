from keras.datasets import boston_housing #导入波士顿房价数据集
import pandas as pd 
import pandas_profiling

(train_x, train_y), (test_x, test_y) = boston_housing.load_data()


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

pandas_profiling.ProfileReport(train_df) 