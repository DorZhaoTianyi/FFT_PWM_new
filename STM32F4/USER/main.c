#include "sys.h"
#include "delay.h"
#include "usart.h"
#include "led.h"
#include "adc_dma_timer.h"
#include "key.h"
#include "timer.h" 
#include "math.h" 
#include "arm_math.h"  
#include "string.h"

//ALIENTEK 探索者STM32F407开发板 实验13
//LCD显示实验-库函数版本
//技术支持：www.openedv.com
//淘宝店铺：http://eboard.taobao.com  
//广州市星翼电子科技有限公司  
//作者：正点原子 @ALIENTEK
#define FFT_LENGTH		1024 		//FFT长度，默认是1024点FFT

float fft_inputbuf[FFT_LENGTH*2];	//FFT输入数组
float fft_outputbuf[FFT_LENGTH];	//FFT输出数组
u32 i=0;
u8 timeout;//定时器溢出次数
int a;

// 串口接收相关变量
u8 usart_rx_buf[20];     // 串口接收缓冲区
u8 usart_rx_cnt = 0;     // 接收计数器
u8 usart_rx_flag = 0;    // 接收完成标志
u32 pwm_value = 0;       // 从串口接收的PWM值

// 全局变量存储Python传来的数据
u32 python_received_data = 0;  // 全局变量，存储从Python接收的数据

// 处理接收到的串口数据
void Process_Serial_Data(void)
{
    u32 received_value = 0;
    u8 i;
    
    if(usart_rx_flag == 1)
    {
        usart_rx_flag = 0;
        
        // 将接收到的字符串转换为整数
        for(i = 0; i < 10; i++)
        {
            if(usart_rx_buf[i] >= '0' && usart_rx_buf[i] <= '9')
            {
                received_value = received_value * 10 + (usart_rx_buf[i] - '0');
            }
        }
        
        // 将接收到的值存储到全局变量
        python_received_data = received_value;
        
        // 将接收到的值乘以100作为PWM值
        pwm_value = received_value * 1;
    }
}

int main(void)
{  
	
    arm_cfft_radix4_instance_f32 scfft;  //初始化定义一个结构体++++++++++++++++++++++++
	
    u8 key,t=0;
    float time; 
    u8 buf[50]; 
    u16 i; 
    u16 pwm_duty = 0;           //PWM占空比变量
    u8 pwm_dir = 0;             //PWM方向控制：0-递增，1-递减

    NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);//设置系统中断优先级分组2
    delay_init(168);  //初始化延时函数
    uart_init(115200);		//初始化串口波特率为115200
    
    // 使能串口接收中断
    USART_ITConfig(USART1, USART_IT_RXNE, ENABLE);
    
    LED_Init();					//初始化LED
    KEY_Init();					//初始化按键
    LCD_Init();					//初始化LCD
    
    ADC_GPIO_Init();						    // ADC引脚初始化
    TIM3_Config( SAM_FRE );                     // 触发ADC采样频率，采样频率2MHz
    ADC_Config();                               // ADC1024采样频率，采集1024个数据
    TIM2_Int_Init(65535,84-1);	                // 1Mhz计数频率,最大计时65ms左右超出
    
    //TIM4 PWM初始化：1kHz频率，初始占空比0%
    //计算公式：PWM频率 = 84MHz / ((arr+1)*(psc+1))
    TIM4_PWM_Init(999, 3359, 0);

    arm_cfft_radix4_init_f32(&scfft,FFT_LENGTH,0,1);//初始化scfft结构体，设定FFT相关参数（需要初始化的结构体，FFT的长度，是否反FFT变换，是否按位取反）
    				 	
    while(1) 
    {		 
			if(pwm_value > 999)
			{
					pwm_value = 999;
			}
				
				// 设置PWM占空比
			TIM4_SetPWM1_Duty(pwm_value);
      key=KEY_Scan(0);
//		if(key==KEY0_PRES)
//		{			 
        ADC_DMA_Trig( ADC1_DMA_Size );          // 开始AD采集，设置采样点数
        delay_ms(2000);                         // 延时3ms，等待ADC数据全部转换到 ADC1_ConvertedValue数组中
        delay_ms(2000);                         // 延时3ms，等待ADC数据全部转换到 ADC1_ConvertedValue数组中

        for(i=0;i<FFT_LENGTH;i++)//生成信号序列
        {
            fft_inputbuf[2*i] = (float)ADC1_ConvertedValue[ i ]*3.3f/4096.0f;//实部为ADC采样值
//			fft_inputbuf[2*i]=100+10*arm_sin_f32(2*PI*i/FFT_LENGTH)+30*arm_sin_f32(2*PI*i*4/FFT_LENGTH)+50*arm_cos_f32(2*PI*i*8/FFT_LENGTH);	//生成输入信号实部

            fft_inputbuf[2*i+1]=0;//虚部全部为0
        }
        TIM_SetCounter(TIM2,0);//重设TIM2定时器的计数器值
        timeout=0;
        
        arm_cfft_radix4_f32(&scfft,fft_inputbuf);	//FFT计算（基4）
        //这里的输入是inputbuf，这里的输出也放倒了inputbuf中
        //每个点对应的频率=采样频率/点数 eg：采样频率为1024Hz，有1024个样本点，那么outbuf[1]对应的就是1Hz对应的幅值
        //outbuf是对称的，只有前512个样本点有效
        
        time=TIM_GetCounter(TIM2)+(u32)timeout*65536; 			//计算所用时间
        sprintf((char*)buf,"%0.3fms\r\n",time/1000);		
        
        arm_cmplx_mag_f32(fft_inputbuf,fft_outputbuf,FFT_LENGTH);	//把运算结果复数求模得幅值 ++++++++++++++++++++++++++++++
        
        for(i=0;i<FFT_LENGTH;i++)
        {
            printf("%f\r\n",fft_outputbuf[i]); //可能有误差，需要在fft_outputbuf[i]后面乘以一个系数+++++++++++++++++++
        }
        
//        //显示原始数据
//        for(i=0;i<FFT_LENGTH;i++)
//        {

//        }

        
        // 处理串口接收数据
        Process_Serial_Data();
        /****************** PWM控制程序结束 ******************/
        t++;	  
        a++;
        
        delay_ms(100);  // 添加适当延时，控制PWM变化速度
    }
}