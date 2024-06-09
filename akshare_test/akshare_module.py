import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import argparse

class AKSHARE():
    def init(self):
        pass

    @staticmethod
    def read_csv(file_name) -> pd:
        data = pd.read_csv(file_name)
        return data

    def get_total_code(self):
        stock_sh_a_spot_em_df = ak.stock_sh_a_spot_em()
        stock_sz_a_spot_em_df = ak.stock_sz_a_spot_em()
        print(stock_sz_a_spot_em_df)
        stock_list = pd.concat([stock_sh_a_spot_em_df[["代码","名称"]], stock_sz_a_spot_em_df[["代码","名称"]]], axis=0)
        return stock_list
    
    def date_iterator(self, start_date):
        current_date = datetime.strptime(start_date, '%Y%m%d')
        end_date = datetime.today()

        while current_date <= end_date:
            yield current_date.strftime('%Y%m%d')
            current_date += timedelta(days=1)

    def merge_dataframes(self, df1, df2, column_name):
        merged_df = pd.merge(df1, df2, on=['代码', '报告期'], how='outer', suffixes=('_df1', '_df2'))
        merged_df[f'{column_name}_df1'] = merged_df[f'{column_name}_df1'].fillna(0)
        merged_df[f'{column_name}_df2'] = merged_df[f'{column_name}_df2'].fillna(0)
        merged_df[column_name] = merged_df[f'{column_name}_df1'] + merged_df[f'{column_name}_df2']
        result_df = merged_df[['代码', '报告期', column_name]]
        return result_df

    def get_top10_shareholder(self, start_date, column_name):
        file_name = f"{column_name}.csv"
        if os.path.exists(file_name):
            stock_holding_df = pd.read_csv(file_name)
            start_date = stock_holding_df['报告期'].max()
            start_date = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y%m%d')
        else:
            stock_holding_df = pd.DataFrame(columns=['代码', '报告期', column_name])
        for date in self.date_iterator(start_date):
            try:
                stock_holding_xinjin_df = ak.stock_gdfx_holding_detail_em(date=date, indicator=column_name, symbol="新进")
                stock_holding_xinjin_df = stock_holding_xinjin_df.groupby(['股票代码', '报告期'], as_index=False)['期末持股-数量'].sum()
                stock_holding_xinjin_df.rename(columns={'股票代码': '代码', '期末持股-数量': column_name}, inplace=True)
                print(stock_holding_xinjin_df)
                stock_holding_df = self.merge_dataframes(stock_holding_df, stock_holding_xinjin_df, column_name)
            except KeyboardInterrupt:
                print("Process interrupted by user. Exiting gracefully...")
                return
            except:
                print(f"{date} have no data")
            try:
                stock_holding_zengjia_df = ak.stock_gdfx_holding_detail_em(date=date, indicator=column_name, symbol="增加")
                stock_holding_zengjia_df = stock_holding_zengjia_df.groupby(['股票代码', '报告期'], as_index=False)['期末持股-数量'].sum()
                stock_holding_zengjia_df.rename(columns={'股票代码': '代码', '期末持股-数量': column_name}, inplace=True)
                print(stock_holding_zengjia_df)
                stock_holding_df = self.merge_dataframes(stock_holding_df, stock_holding_zengjia_df, column_name)
            except KeyboardInterrupt:
                print("Process interrupted by user. Exiting gracefully...")
                return
            except:
                print(f"{date} have no data")
            try:
                stock_holding_bubian_df = ak.stock_gdfx_holding_detail_em(date=date, indicator=column_name, symbol="不变")
                stock_holding_bubian_df = stock_holding_bubian_df.groupby(['股票代码', '报告期'], as_index=False)['期末持股-数量'].sum()
                stock_holding_bubian_df.rename(columns={'股票代码': '代码', '期末持股-数量': column_name}, inplace=True)
                print(stock_holding_bubian_df)
                stock_holding_df = self.merge_dataframes(stock_holding_df, stock_holding_bubian_df, column_name)
            except KeyboardInterrupt:
                print("Process interrupted by user. Exiting gracefully...")
                return
            except:
                print(f"{date} have no data")
            try:
                stock_holding_jianshao_df = ak.stock_gdfx_holding_detail_em(date=date, indicator=column_name, symbol="减少")
                stock_holding_jianshao_df = stock_holding_jianshao_df.groupby(['股票代码', '报告期'], as_index=False)['期末持股-数量'].sum()
                stock_holding_jianshao_df.rename(columns={'股票代码': '代码', '期末持股-数量': column_name}, inplace=True)
                print(stock_holding_jianshao_df)
                stock_holding_df = self.merge_dataframes(stock_holding_df, stock_holding_jianshao_df, column_name)
            except KeyboardInterrupt:
                print("Process interrupted by user. Exiting gracefully...")
                return
            except:
                print(f"{date} have no data")
            print(stock_holding_df)
            stock_holding_df.to_csv(f"{column_name}.csv", index=False)
            time.sleep(1)

    def get_zong_gu_ben(self):
        stock_zh_a_gdhs_df = ak.stock_zh_a_gdhs(symbol="20231231")
        stock_zh_a_gdhs_df['代码'] = stock_zh_a_gdhs_df['代码'].astype(int)
        stock_zh_a_gdhs_df = stock_zh_a_gdhs_df.sort_values(by='代码')
        stock_zh_a_gdhs_df['代码'] = stock_zh_a_gdhs_df['代码'].apply(lambda x: f"{x:06}")
        print(stock_zh_a_gdhs_df.columns)
        stock_zh_a_gdhs_df.to_csv("total_list.csv", index=False)
        print(stock_zh_a_gdhs_df)

    def merge_dataframes(self, df1, df2):
        second_col_name = df2.columns[2]
        df2['报告期'] = pd.to_datetime(df2['报告期'])
        df2_latest = df2.loc[df2.groupby('代码')['报告期'].idxmax()]
        merged_df = df1.merge(df2_latest[['代码', second_col_name]], on='代码', how='left')
        merged_df[second_col_name] = merged_df[second_col_name].fillna(0)
        return merged_df

    def create_total_list(self):
        new_pd = pd.read_csv("total_list.csv", dtype={'代码': str})[["代码", "名称", "总市值", "总股本"]]
        print(new_pd)
        for name in ["社保","基金","券商","信托","QFII"]:
            input_pd = pd.read_csv(f"{name}.csv")
            print(input_pd)
            new_pd = self.merge_dataframes(new_pd, input_pd)
        print(new_pd)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', help='运行模式')
    args = parser.parse_args()
    # data = pd.read_csv("total_list.csv", dtype={'代码': str})[["代码", "名称", "总市值", "总股本"]]
    # data['社保占比'] = 0
    # print(data)
    # AKSHARE().get_zong_gu_ben()
    if args.mode == "ut10":
        for name in ["社保","基金","券商","信托","QFII"]:
            AKSHARE().get_top10_shareholder("20231231", name)
    if args.mode == "utl":
        AKSHARE().get_zong_gu_ben()
    if args.mode == "ctl":
        AKSHARE().create_total_list()