"""测试天气API解析逻辑"""
import requests

def test_weather_parsing():
    """测试不同格式的天气数据解析"""
    
    test_cases = [
        "Smoky haze +30C 12km/h",  # 你遇到的错误案例
        "晴 +25°C 北风2级 45%",     # 正常中文格式
        "Light rain +20°C SW 15 km/h 60%",  # 英文多词天气
        "Partly cloudy +18°C NE 10km/h 55%",  # 另一个英文案例
        "Clear +32°C Calm 30%",   # 简单英文
    ]
    
    for test_data in test_cases:
        print(f"\n{'='*60}")
        print(f"测试数据: {test_data}")
        print(f"{'='*60}")
        
        parts = test_data.split()
        print(f"分割结果: {parts}")
        
        if len(parts) >= 3:
            # 智能解析：从后往前识别各个字段
            humidity = "未知"
            wind = "未知"
            temperature = "未知"
            condition_parts = []
            
            # 策略1：查找湿度（包含%符号）
            humidity_idx = -1
            for i in range(len(parts) - 1, -1, -1):
                if '%' in parts[i]:
                    humidity = parts[i]
                    humidity_idx = i
                    break
            
            # 策略2：查找温度（包含°C、°F或单独C/F）
            temp_idx = -1
            for i in range(len(parts) - 1, -1, -1):
                if '°' in parts[i] or (parts[i].endswith('C') and len(parts[i]) > 1) or parts[i].endswith('F'):
                    # 确保不是风力描述（如"SW"、"NE"等）
                    if not parts[i].isalpha() or len(parts[i]) > 2:
                        temperature = parts[i]
                        temp_idx = i
                        break
            
            # 策略3：根据位置推断
            if temp_idx > 0:
                # 温度后面的部分是风力和湿度
                remaining = parts[temp_idx + 1:]
                if humidity_idx > temp_idx:
                    # 湿度在温度后面
                    wind_parts = parts[temp_idx + 1:humidity_idx]
                    wind = ' '.join(wind_parts) if wind_parts else "未知"
                else:
                    # 没有明确湿度，剩余的都是风力
                    wind = ' '.join(remaining) if remaining else "未知"
                
                # 温度前面的是天气描述
                condition_parts = parts[:temp_idx]
            else:
                # 没找到温度，使用简单策略：最后3个是温度、风力、湿度
                if len(parts) >= 3:
                    temperature = parts[-3]
                    wind = parts[-2]
                    humidity = parts[-1] if '%' in parts[-1] else "未知"
                    condition_parts = parts[:-3]
                else:
                    condition_parts = parts
            
            condition = ' '.join(condition_parts) if condition_parts else "未知"
            
            print(f"✅ 解析结果:")
            print(f"   天气状况: {condition}")
            print(f"   气温: {temperature}")
            print(f"   风力: {wind}")
            print(f"   湿度: {humidity}")
            print(f"   格式化: 实时天气：{condition}，气温：{temperature}，风力：{wind}，湿度：{humidity}")
        else:
            print(f"❌ 数据不完整: {test_data}")

if __name__ == "__main__":
    test_weather_parsing()
