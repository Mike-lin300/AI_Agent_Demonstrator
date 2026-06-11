import requests
import json
import time

# ================= 配置区域 =================
USE_PROXY = False  # 如果你开了梯子，改为 True
PROXY_URL = "http://127.0.0.1:7890"  # 根据你的代理端口修改


# ===========================================

def get_proxies():
    if USE_PROXY:
        return {"http": PROXY_URL, "https": PROXY_URL}
    return None


def test_wttrin(city="杭州"):
    """测试 wttr.in 天气 API"""
    print(f"\n[测试1] 使用 wttr.in 查询 {city} 天气...")
    url = f"https://wttr.in/{city}?format=%C+%t+%w+%h&lang=zh"
    headers = {"User-Agent": "curl/7.68.0"}  # wttr.in 建议的 UA
    try:
        resp = requests.get(url, headers=headers, proxies=get_proxies(), timeout=10)
        if resp.status_code == 200:
            text = resp.text.strip()
            print(f"✓ 成功！返回内容：{text}")
            # 尝试提取温度数值
            import re
            temp_match = re.search(r'([+-]?\d+)°C', text)
            if temp_match:
                print(f"  提取温度数值：{temp_match.group(1)}")
            return True
        else:
            print(f"✗ 失败，HTTP状态码：{resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ 异常：{str(e)}")
        return False


def test_openmeteo(city="杭州"):
    """测试 Open-Meteo 天气 API（需要先获取城市坐标）"""
    print(f"\n[测试2] 使用 Open-Meteo 查询 {city} 天气...")

    # 先用 geocoding API 获取坐标（Open-Meteo 免费，无需密钥）
    geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=zh"
    try:
        resp = requests.get(geocode_url, proxies=get_proxies(), timeout=10)
        if resp.status_code != 200:
            print(f"✗ 地理编码失败，状态码：{resp.status_code}")
            return False
        data = resp.json()
        if not data.get("results"):
            print(f"✗ 未找到城市 {city}")
            return False
        lat = data["results"][0]["latitude"]
        lon = data["results"][0]["longitude"]
        name = data["results"][0]["name"]

        # 获取当前天气
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
        resp2 = requests.get(weather_url, proxies=get_proxies(), timeout=10)
        if resp2.status_code != 200:
            print(f"✗ 天气查询失败，状态码：{resp2.status_code}")
            return False
        weather = resp2.json()["current_weather"]
        temperature = weather["temperature"]
        windspeed = weather["windspeed"]
        weathercode = weather["weathercode"]
        # 简单的天气代码映射（0-晴天，1-多云，2-阴，3-雨等）
        code_map = {0: "晴", 1: "多云", 2: "阴", 3: "小雨", 45: "雾", 51: "毛毛雨"}
        condition = code_map.get(weathercode, "未知")
        print(f"✓ 成功！{name} 当前天气：{condition}，温度：{temperature}°C，风速：{windspeed} km/h")
        return True
    except Exception as e:
        print(f"✗ 异常：{str(e)}")
        return False


if __name__ == "__main__":
    print("===== 天气 API 连通性测试 =====")
    city = input("请输入城市名称（默认杭州）：").strip()
    if not city:
        city = "杭州"

    # 测试 wttr.in
    ok1 = test_wttrin(city)
    # 测试 Open-Meteo
    ok2 = test_openmeteo(city)

    print("\n===== 测试结果 =====")
    if ok1:
        print("✅ wttr.in 可用，推荐使用。")
    else:
        print("❌ wttr.in 不可用，可能被墙或网络问题。")

    if ok2:
        print("✅ Open-Meteo 可用，可作为备选。")
    else:
        print("❌ Open-Meteo 不可用。")

    if not (ok1 or ok2):
        print("\n⚠️ 两种 API 均失败，请检查：")
        print("1. 网络连接（尝试关闭代理或将 USE_PROXY 改为 True）")
        print("2. 安装 requests 库：pip install requests")
        print("3. 如果使用了代理，确认 PROXY_URL 端口正确")