import matplotlib.pyplot as plt
import numpy as np
import serial
import time

plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示符号

# 串口配置
recv_port = 'COM17'  # 接收数据的串口号
send_port = 'COM15'  # 发送数据的串口号
baudrate = 115200  # 波特率
timeout = 1  # 超时时间

# 打开接收串口
try:
    ser_recv = serial.Serial(recv_port, baudrate, timeout=timeout)
    print(f"接收串口 {recv_port} 已打开")
except Exception as e:
    print(f"无法打开接收串口 {recv_port}: {e}")
    exit()

# 打开发送串口
try:
    ser_send = serial.Serial(send_port, baudrate, timeout=timeout)
    print(f"发送串口 {send_port} 已打开")
except Exception as e:
    print(f"无法打开发送串口 {send_port}: {e}")
    ser_recv.close()
    exit()

# 初始化数据缓冲区
data_buffer = []
buffer_size = 1024  # 每次处理的数据点数

# 忽略的索引集合
ignore_indices = {0, 48, 49, 50, 51, 52, 150, 774, 874, 974, 250,924,100,1010,274,1023,997}


# 动态更新函数
def update_plots(data):
    if len(data) > 0:
        # 获取所有索引按值降序排序
        sorted_indices = np.argsort(data)[::-1]  # 降序排列索引

        # 找到第一个有效的索引
        valid_index = None
        for idx in sorted_indices:
            if idx not in ignore_indices:
                valid_index = idx
                break

        if valid_index is not None:
            try:
                # 将有效索引转换为字符串，长度固定为10字节
                index_str = str(valid_index).zfill(10)  # 补0至10字节
                index_bytes = index_str.encode('utf-8')

                # 发送索引数据
                ser_send.write(index_bytes)
                print(index_str)
            except Exception as e:
                print(f"发送串口发送失败: {e}")
        else:
            print("未找到有效索引")
    else:
        print("未找到有效数据")


# 主循环
try:
    while True:
        if ser_recv.in_waiting > 0:
            line = ser_recv.readline().decode('utf-8').strip()  # 读取一行数据并解码
            try:
                value = float(line)  # 将数据转换为浮点数
                data_buffer.append(value)

                if len(data_buffer) >= buffer_size:
                    update_plots(np.array(data_buffer))  # 处理数据并发送最大值索引
                    data_buffer = []  # 清空缓冲区
            except ValueError:
                print(f"忽略无效数据: {line}")
except KeyboardInterrupt:
    print("程序已停止")
finally:
    ser_recv.close()  # 关闭接收串口
    ser_send.close()  # 关闭发送串口
    print("串口已关闭")
