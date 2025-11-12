#!/usr/bin/python
# -*- coding:utf-8 -*-
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn import svm
import time
import serial

start_time = time.time()

plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示符号

# 串口配置 - 使用同一个串口
com_port = 'COM16'  # 使用同一个串口号
baudrate = 115200  # 波特率
timeout = 1  # 超时时间

# 打开串口
try:
    ser = serial.Serial(com_port, baudrate, timeout=timeout)
    print(f"串口 {com_port} 已打开")
except Exception as e:
    print(f"无法打开串口 {com_port}: {e}")
    exit()

# 初始化数据缓冲区
data_buffer = []
buffer_size = 1024  # 每次处理的数据点数

# 忽略的索引集合
ignore_indices = {0, 48, 49, 50, 51, 52,71,72,13}  # 固定忽略的索引
ignore_indices.update(range(100, 1024))  # 忽略100-1023的所有数

# 用于记录发送数据的变量
send_count = 0
send_data_log = []

# 动态更新函数
def update_plots(data):
    global send_count, send_data_log
    
    if len(data) > 0:
        # 获取所有索引按值降序排序
        sorted_indices = np.argsort(data)[::-1]

        # 找到第一个有效的索引
        valid_index = None
        for idx in sorted_indices:
            if idx not in ignore_indices:
                valid_index = idx
                print(f"有效索引: {valid_index}")
                break

        if valid_index is not None:
            try:
                # 修改这里：添加 [0] 确保 y_hat 是标量
                x_test = np.array([[valid_index]])
                y_hat = svr_rbf.predict(x_test)[0] * 1000  # 添加 [0]
                y_hat_int = int(y_hat)

                # 将预测值转换为字符串，长度固定为10字节
                y_str = str(y_hat_int).zfill(10)  # 补0至10字节
                y_bytes = y_str.encode('utf-8')

                # 发送数据 - 使用同一个串口
                bytes_sent = ser.write(y_bytes)
                
                # 记录发送数据
                send_count += 1
                send_data_log.append({
                    'timestamp': time.time(),
                    'valid_index': valid_index,
                    'predicted_value': y_hat,
                    'integer_value': y_hat_int,
                    'formatted_string': y_str,
                    'bytes_sent': bytes_sent,
                    'hex_data': y_bytes.hex()
                })
                
                # 打印发送的内容（详细版本）
                print("=" * 50)
                print(f"第 {send_count} 次发送:")
                print(f"有效索引: {valid_index}")
                print(f"原始预测值: {y_hat:.4f}")
                print(f"整数预测值: {y_hat_int}")
                print(f"格式化字符串: '{y_str}'")
                print(f"字节数据: {y_bytes}")
                print(f"实际发送字节数: {bytes_sent}")
                print(f"十六进制: {y_bytes.hex()}")
                
                # 检查发送缓冲区状态
                if ser.out_waiting > 0:
                    print(f"发送缓冲区剩余字节: {ser.out_waiting}")
                else:
                    print("发送缓冲区已清空")
                    
                print("=" * 50)
                
            except Exception as e:
                print(f"串口发送失败: {e}")
        else:
            print("未找到有效索引")
    else:
        print("未找到有效数据")

# 新增函数：显示发送统计信息
def show_send_statistics():
    print("\n" + "="*60)
    print("串口发送数据统计")
    print("="*60)
    print(f"总发送次数: {send_count}")
    
    if send_count > 0:
        print(f"最近一次发送数据: {send_data_log[-1]['formatted_string']}")
        print(f"最近一次发送的十六进制: {send_data_log[-1]['hex_data']}")
        
        # 显示最近5次发送记录
        print("\n最近5次发送记录:")
        print("-" * 40)
        for i, log in enumerate(send_data_log[-5:], 1):
            print(f"{i}. 索引:{log['valid_index']} -> 预测值:{log['predicted_value']:.2f} -> 发送:'{log['formatted_string']}'")
    
    print("="*60)

if __name__ == "__main__":
    # pandas读入
    data = pd.read_csv('SSDVA_shift.csv')
    x = data[['Freq']]
    y = data['Current']
    print("训练数据特征:")
    print(x)
    print("训练数据标签:")
    print(y)
    
    # 生成等间距的索引划分数据集
    indices = np.linspace(0, len(x) - 1, num=3, dtype=int)

    # 使用索引划分数据集
    x_train = x.loc[indices]
    y_train = y.loc[indices]
    x_test = x.drop(indices)
    y_test = y.drop(indices)

    # 选用高斯核函数的SVM
    svr_rbf = svm.SVR(kernel='poly', degree=5, gamma=0.01, C=0.1)
    # 拟合函数
    svr_rbf.fit(x_train, y_train.to_numpy())

    # 在测试集进行预测
    y_hat = svr_rbf.predict(x_test)  # 在测试集进行预测，x_test是我的输入，y_hat是输出
    end_time = time.time()
    execution_time = end_time - start_time
    mse = np.average((y_hat - y_test) ** 2)  # Mean Squared Error
    rmse = np.sqrt(mse)  # Root Mean Squared Error
    
    print(f"\n模型训练完成")
    print(f"训练用时: {execution_time:.2f}秒")
    print(f"均方误差: {mse:.4f}")
    print(f"均方根误差: {rmse:.4f}")
    print("\n开始监听串口数据...")

    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()  # 读取一行数据并解码
                print(f"\n接收到串口数据: '{line}'")
                try:
                    value = float(line)  # 将数据转换为浮点数
                    data_buffer.append(value)
                    print(f"成功转换为数值: {value}")
                    print(f"当前缓冲区数据量: {len(data_buffer)}/{buffer_size}")

                    if len(data_buffer) >= buffer_size:
                        print("\n缓冲区已满，开始处理数据...")
                        update_plots(np.array(data_buffer))  # 处理数据并发送预测值
                        # 每处理10次数据显示一次统计信息
                        if send_count % 10 == 0:
                            show_send_statistics()
                            
                        data_buffer = []  # 清空缓冲区
                        print("缓冲区已清空")
                except ValueError:
                    print(f"忽略无效数据: '{line}'")
                    
            # 每30秒显示一次统计信息（即使没有新数据）
            if time.time() % 30 < 0.1 and send_count > 0:
                show_send_statistics()
                time.sleep(0.2)  # 避免重复触发
                
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        show_send_statistics()
    except Exception as e:
        print(f"\n程序异常: {e}")
        show_send_statistics()
    finally:
        ser.close()  # 关闭串口
        print("串口已关闭")





