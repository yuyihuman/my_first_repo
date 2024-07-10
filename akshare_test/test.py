import pandas as pd

class DataProcessor:
    def sort_and_select_top_n(self, df, column_name, n=10, max_market_value=None, min_market_value=None):
        # 复制总市值列并转换为纯数字
        df_copy = df.copy()
        df_copy['总市值(亿)_数值'] = df_copy['总市值(亿)'].str.extract('(\d+\.?\d*)').astype(float)
        
        # 过滤总市值（亿）的范围
        if max_market_value is not None:
            df_copy = df_copy[df_copy['总市值(亿)_数值'] <= max_market_value]
        if min_market_value is not None:
            df_copy = df_copy[df_copy['总市值(亿)_数值'] >= min_market_value]
        
        # 按指定列排序
        sorted_df = df_copy.sort_values(by=column_name, ascending=False)
        
        # 选择前n行
        top_n_df = sorted_df.head(n)
        
        # 删除临时列
        top_n_df = top_n_df.drop(columns=['总市值(亿)_数值'])
        
        return top_n_df

# 假设你有一个DataFrame命名为df
df = pd.DataFrame({
    '代码': ['000001', '000002', '000004', '000006', '000007'],
    '名称': ['平安银行', '万科A', '国华网安', '深振业A', '*ST全新'],
    '总市值(亿)': ['1822.2亿', '1017.2亿', '21.4亿', '62.0亿', '16.9亿'],
    '总股本': [1.940592e+10, 9.724197e+09, 1.323803e+08, 1.349995e+09, 3.464480e+08],
    '社保': [0.0, 0.0, 0.0, 0.0, 0.0],
    '基金': [0.012, 0.022, 0.0, 0.005, 0.0],
    '券商': [0.000, 0.000, 0.000, 0.000, 0.000],
    '信托': [0.0, 0.0, 0.0, 0.0, 0.0],
    'QFII': [0.0, 0.0, 0.0, 0.0, 0.0]
})

# 使用类中的方法
processor = DataProcessor()
result = processor.sort_and_select_top_n(df, column_name='总市值(亿)', n=3, max_market_value=1000, min_market_value=20)
print(result)
