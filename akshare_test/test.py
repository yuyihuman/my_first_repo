import pandas as pd

def merge_dataframes(df1, df2):
    # 合并两个 DataFrame
    merged_df = pd.merge(df1, df2, on=['代码', '报告期'], how='outer', suffixes=('_df1', '_df2'))
    
    # 填充缺失值
    merged_df['社保持股_df1'] = merged_df['社保持股_df1'].fillna(0)
    merged_df['社保持股_df2'] = merged_df['社保持股_df2'].fillna(0)
    
    # 新列 "社保持股" 是两个列相加
    merged_df['社保持股'] = merged_df['社保持股_df1'] + merged_df['社保持股_df2']
    
    # 选择所需的列
    result_df = merged_df[['代码', '报告期', '社保持股']]
    
    return result_df

# 示例 DataFrame
data1 = {
    '代码': ['000039', '000400', '000543', '000837'],
    '报告期': ['2024-03-31', '2024-03-31', '2024-03-31', '2024-03-31'],
    '社保持股': [24822150, 5986300, 15652680, 8303700]
}

data2 = {
    '代码': ['000039', '000400', '601101', '603659'],
    '报告期': ['2024-03-31', '2024-03-31', '2024-03-31', '2024-03-31'],
    '社保持股': [5000000, 2000000, 10406260, 14876319]
}



df1 = pd.DataFrame(data1)
df2 = pd.DataFrame(data2)
print(df1)
print(df2)
# 合并两个 DataFrame
result_df = merge_dataframes(df1, df2)

# 打印结果
print(result_df)
