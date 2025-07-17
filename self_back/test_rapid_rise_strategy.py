#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
10分钟快速上涨策略测试脚本

测试新增的10分钟快速上涨买入策略和参数化配置功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import run_continuous_strategy_backtest
from modules.buy_strategy import BuyStrategy
from modules.sell_strategy import SellStrategy
from utils.logger import setup_logger

def test_rapid_rise_strategy():
    """
    测试10分钟快速上涨策略
    """
    logger = setup_logger('test_rapid_rise', 'test_rapid_rise.log')
    logger.info("开始测试10分钟快速上涨策略")
    
    # 设置测试日期范围为最近一个月
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    test_start_date = start_date.strftime('%Y%m%d')
    test_end_date = end_date.strftime('%Y%m%d')
    
    logger.info(f"测试日期范围: {test_start_date} - {test_end_date}")
    print(f"📅 测试日期范围: {test_start_date} - {test_end_date}")
    
    print("\n" + "=" * 60)
    print("🧪 10分钟快速上涨策略测试")
    print("=" * 60)
    
    try:
        # 测试1：验证策略注册
        print("\n=== 测试1：验证策略注册 ===")
        buy_strategy = BuyStrategy()
        available_strategies = buy_strategy.get_available_strategies()
        
        print(f"可用买入策略: {available_strategies}")
        
        if 'rapid_rise_10min' in available_strategies:
            print("✅ 10分钟快速上涨策略已成功注册")
        else:
            print("❌ 10分钟快速上涨策略未注册")
            return False
        
        # 测试2：参数化策略配置
        print("\n=== 测试2：参数化策略配置测试 ===")
        
        # 配置1：默认参数（3%上涨阈值，10分钟窗口）
        print("\n--- 配置1：默认参数 ---")
        buy_config_1 = {
            'strategy_name': 'rapid_rise_10min',
            'params': {
                'rise_threshold': 0.03,      # 3%上涨阈值
                'time_window_minutes': 10    # 10分钟时间窗口
            }
        }
        
        sell_config_1 = {
            'strategy_name': 'hold_three_days',
            'params': {}
        }
        
        print(f"买入策略配置: {buy_config_1}")
        print(f"卖出策略配置: {sell_config_1}")
        
        # 配置2：更激进的参数（2%上涨阈值，5分钟窗口）
        print("\n--- 配置2：更激进参数 ---")
        buy_config_2 = {
            'strategy_name': 'rapid_rise_10min',
            'params': {
                'rise_threshold': 0.02,      # 2%上涨阈值
                'time_window_minutes': 5     # 5分钟时间窗口
            }
        }
        
        sell_config_2 = {
            'strategy_name': 'stop_profit_loss',
            'params': {
                'stop_loss_pct': 0.05,       # 5%止损
                'take_profit_pct': 0.10,     # 10%止盈
                'max_hold_days': 5           # 最大持有5天
            }
        }
        
        print(f"买入策略配置: {buy_config_2}")
        print(f"卖出策略配置: {sell_config_2}")
        
        # 配置3：保守参数（5%上涨阈值，15分钟窗口）
        print("\n--- 配置3：保守参数 ---")
        buy_config_3 = {
            'strategy_name': 'rapid_rise_10min',
            'params': {
                'rise_threshold': 0.05,      # 5%上涨阈值
                'time_window_minutes': 15    # 15分钟时间窗口
            }
        }
        
        sell_config_3 = {
            'strategy_name': 'hold_three_days',
            'params': {}
        }
        
        print(f"买入策略配置: {buy_config_3}")
        print(f"卖出策略配置: {sell_config_3}")
        
        # 测试3：运行策略回测
        print("\n=== 测试3：运行策略回测 ===")
        
        test_configs = [
            ("默认参数", buy_config_1, sell_config_1),
            ("激进参数", buy_config_2, sell_config_2),
            ("保守参数", buy_config_3, sell_config_3)
        ]
        
        for config_name, buy_config, sell_config in test_configs:
            print(f"\n--- 测试配置：{config_name} ---")
            try:
                print(f"🔄 运行{config_name}策略回测...")
                # 使用缩短的日期范围进行测试
                import sys
                sys.argv = ['main.py', '--start_date', test_start_date, '--end_date', test_end_date]
                run_continuous_strategy_backtest(
                    buy_strategy_config=buy_config,
                    sell_strategy_config=sell_config
                )
                print(f"✅ {config_name}策略回测完成")
            except Exception as e:
                print(f"❌ {config_name}策略回测失败: {str(e)}")
                logger.error(f"{config_name}策略回测失败: {str(e)}", exc_info=True)
        
        print("\n=== 10分钟快速上涨策略测试完成 ===")
        return True
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}", exc_info=True)
        print(f"❌ 测试失败: {str(e)}")
        return False

def test_strategy_comparison():
    """
    测试不同策略的对比
    """
    print("\n" + "=" * 60)
    print("📊 策略对比测试")
    print("=" * 60)
    
    # 策略对比配置
    strategies_to_compare = [
        {
            'name': '连续三天上涨策略',
            'buy_config': {
                'strategy_name': 'three_days_up',
                'params': {}
            },
            'sell_config': {
                'strategy_name': 'hold_three_days',
                'params': {}
            }
        },
        {
            'name': '10分钟快速上涨策略（3%）',
            'buy_config': {
                'strategy_name': 'rapid_rise_10min',
                'params': {
                    'rise_threshold': 0.03,
                    'time_window_minutes': 10
                }
            },
            'sell_config': {
                'strategy_name': 'hold_three_days',
                'params': {}
            }
        },
        {
            'name': '10分钟快速上涨策略（2%）',
            'buy_config': {
                'strategy_name': 'rapid_rise_10min',
                'params': {
                    'rise_threshold': 0.02,
                    'time_window_minutes': 10
                }
            },
            'sell_config': {
                'strategy_name': 'stop_profit_loss',
                'params': {
                    'stop_loss_pct': 0.05,
                    'take_profit_pct': 0.10,
                    'max_hold_days': 5
                }
            }
        }
    ]
    
    # 设置测试日期范围为最近一个月
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    test_start_date = start_date.strftime('%Y%m%d')
    test_end_date = end_date.strftime('%Y%m%d')
    
    print(f"📅 策略对比测试日期范围: {test_start_date} - {test_end_date}")
    
    for strategy in strategies_to_compare:
        print(f"\n--- 测试策略：{strategy['name']} ---")
        try:
            # 使用缩短的日期范围进行测试
            import sys
            sys.argv = ['main.py', '--start_date', test_start_date, '--end_date', test_end_date]
            run_continuous_strategy_backtest(
                buy_strategy_config=strategy['buy_config'],
                sell_strategy_config=strategy['sell_config']
            )
            print(f"✅ {strategy['name']}测试完成")
        except Exception as e:
            print(f"❌ {strategy['name']}测试失败: {str(e)}")

def main():
    """
    主函数
    """
    print("开始10分钟快速上涨策略和参数化配置测试...")
    
    # 测试基本功能
    success = test_rapid_rise_strategy()
    
    if success:
        print("\n✅ 基本功能测试成功")
        
        # 进行策略对比测试
        print("\n🔄 开始策略对比测试...")
        test_strategy_comparison()
        
        print("\n✅ 所有测试完成")
    else:
        print("\n❌ 基本功能测试失败")
    
    print("\n详细日志请查看 test_rapid_rise.log 文件")

if __name__ == '__main__':
    main()