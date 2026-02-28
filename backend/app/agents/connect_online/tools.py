import json
from typing import Union, List, Dict, Any
from agentscope.message import TextBlock
from agentscope.tool import ToolResponse
from dotenv import load_dotenv
import requests
import os
import ssl
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

from backend.app.agents.tool_input_sanitizer import sanitize_tool_inputs

load_dotenv()


def make_http_request(url: str, params: dict, timeout: int = 10) -> dict:
    """
    通用HTTP GET请求函数，用于简化重复代码。

    Args:
        url (str): 请求URL。
        params (dict): 请求参数。
        timeout (int): 超时时间，默认为10秒。

    Returns:
        dict: 解析后的JSON响应数据。

    Raises:
        requests.RequestException: 请求失败时抛出异常。
    """
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"HTTP请求失败：{str(e)}")


def search_web(query: str) -> ToolResponse:
    """{使用 Brave Search 或 SerpAPI 进行联网搜索（优先 Brave）}
    Args:
        query (str):
            {联网搜索的查询语句}
    """
    brave_key = os.getenv("BRAVE_SEARCH_API_KEY")
    serp_key = os.getenv("SERPAPI_API_KEY")
    if not brave_key and not serp_key:
        content = "BRAVE_SEARCH_API_KEY 或 SERPAPI_API_KEY 未设置"
        text_block = TextBlock(type="text", text=content)
        return ToolResponse(content=[text_block])

    # 优先使用 Brave
    if brave_key:
        params = {
            "q": query,
            "count": 5,
            "safesearch": "moderate",
            "country": "CN",
            "search_lang": "zh-hans",
        }
        headers = {"X-Subscription-Token": brave_key}
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params=params,
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("web", {}).get("results", [])[:5]:
            title = item.get("title")
            snippet = item.get("description")
            link = item.get("url")
            results.append(f"- {title}\n  {snippet}\n  {link}")
        text = "\n".join(results) if results else "No results found."
        text_block = TextBlock(type="text", text=text)
        return ToolResponse(content=[text_block])

    # 回退到 SerpAPI
    params = {
        "engine": "google",
        "q": query,
        "hl": "zh-cn",
        "num": 5,
        "api_key": serp_key,
    }
    resp = requests.get("https://serpapi.com/search", params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("organic_results", [])[:5]:
        title = item.get("title")
        snippet = item.get("snippet")
        link = item.get("link")
        results.append(f"- {title}\n  {snippet}\n  {link}")

    text = "\n".join(results) if results else "No results found."
    text_block = TextBlock(type="text", text=text)
    return ToolResponse(content=[text_block])


def geocode(address: str):
    """地址转经纬度"""
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "key": os.getenv("AMAP_KEY"),
        "address": address,
        "output": "json",
    }

    resp = requests.get(url, params=params, timeout=10).json()
    if resp.get("status") != "1" or not resp.get("geocodes"):
        return None
    return resp["geocodes"][0]["location"]


def search_amap_drive(start: str, end: str) -> ToolResponse:
    """{使用高德地图 API 查询驾车路线}
    Args:
        start (str):
            {路线规划起始地}
        end (str):
            {路线规划目的地}
    """
    try:
        origin = geocode(start)
        destination = geocode(end)

        if not origin or not destination:
            content = f"路线规划失败：无法解析起点或终点地址（{start} -> {end}）"
            text_block = TextBlock(type="text", text=content)
            return ToolResponse(
                content=[text_block]
            )

        url = "https://restapi.amap.com/v3/direction/driving"
        params = {
            "key": os.getenv("AMAP_KEY"),
            "origin": origin,
            "destination": destination,
            "output": "json",
        }

        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "1":
            content = f"路线规划失败：{data.get('info', '未知错误')}"
            text_block = TextBlock(type="text", text=content)
            return ToolResponse(
                content=[text_block]
            )

        paths = data.get("route", {}).get("paths", [])
        if not paths:
            content = "路线规划失败：未返回可用路径"
            text_block = TextBlock(type="text", text=content)
            return ToolResponse(content=[text_block])

        steps = paths[0].get("steps", [])
        if not steps:
            content = "路线规划失败：路径中无导航步骤"
            text_block = TextBlock(type="text", text=content)
            return ToolResponse(content=[text_block])

        step_texts = []
        for i, step in enumerate(steps, 1):
            instruction = (
                step.get("instruction", "")
                .replace("<b>", "")
                .replace("</b>", "")
            )
            step_texts.append(f"{i}. {instruction}")

        text = (
            f"从“{start}”到“{end}”的驾车路线如下：\n\n"
            + "\n".join(step_texts)
        )
        text_block = TextBlock(type="text", text=text)
        return ToolResponse(content=[text_block])

    except Exception as e:
        content = f"路线规划失败：{str(e)}"
        text_block = TextBlock(type="text", text=content)
        return ToolResponse(content=[text_block])


def search_weather(location: str) -> ToolResponse:
    """{使用心知天气 API 查询指定地点当前天气}
    Args:
        location (str):
            {获取实时天气的地址}
    """
    try:
        url = "https://api.seniverse.com/v3/weather/now.json"
        params = {
            "key": os.getenv("XINZHI_WEATHER_KEY"),
            "location": location,
            "language": "zh-Hans",
            "unit": "c",
        }

        response = make_http_request(url, params=params, timeout=10)

        if not isinstance(response, dict) or not response.get("results"):
            # 处理无结果的情况
            text_block = TextBlock(type="text", text=f"天气查询失败：{response.get('status', '未知错误')}")
            return ToolResponse(
                content=[text_block]
            )

        weather_data = response["results"][0]
        location_name = weather_data.get("location", {}).get("name", location)
        now = weather_data.get("now", {})

        def g(key, default="未知"):
            return now.get(key, default)

        text = (
            f"地点：{location_name}\n"
            f"天气状况：{g('text')}\n"
            f"温度：{g('temperature')}°C\n"
            f"体感温度：{g('feels_like')}°C\n"
            f"风向：{g('wind_direction')}\n"
            f"风力等级：{g('wind_scale')}级\n"
            f"风速：{g('wind_speed')} km/h\n"
            f"湿度：{g('humidity')}%\n"
            f"降水量：{g('precip')} mm\n"
            f"能见度：{g('visibility')} km\n"
            f"气压：{g('pressure')} hPa\n"
            f"更新时间：{g('last_update')}"
        )
        text_block = TextBlock(type="text", text=text)
        return ToolResponse(content=[text_block])

    except Exception as e:
        text_block = TextBlock(type="text", text=f"天气查询过程中发生异常：{str(e)}")
        return ToolResponse(
            content=[text_block]
        )


def search_weather_forecast(location: str, days: int = 3) -> ToolResponse:
    """{使用心知天气 API 查询指定地点未来天气预报}
    Args:
        location (str):
            {查看天气的地址精确到县}
        days (int):
            {查看该地区的未来天气的预测天数}
    """
    try:
        url = "https://api.seniverse.com/v3/weather/daily.json"
        params = {
            "key": os.getenv("XINZHI_WEATHER_KEY"),
            "location": location,
            "language": "zh-Hans",
            "unit": "c",
            "start": 0,
            "days": min(days, 15),
        }

        response = make_http_request(url, params=params)

        if not response.get("results"):
            text_block = TextBlock(type="text", text=f"天气查询失败：{response.get('status', '未知错误')}")
            return ToolResponse(
                content=[text_block]
            )

        weather_data = response["results"][0]
        location_name = weather_data.get("location", {}).get("name", location)
        daily_data = weather_data.get("daily", [])

        forecast_list = []
        for i, day in enumerate(daily_data, 1):
            def d(key, default="未知"):
                return day.get(key, default)

            forecast_info = (
                f"第{i}天（{d('date')}）：\n"
                f"白天：{d('text_day')}，夜间：{d('text_night')}\n"
                f"最高温度：{d('high')}°C，最低温度：{d('low')}°C\n"
                f"风向：{d('wind_direction')}，风力：{d('wind_scale')}级\n"
                f"降水概率：{d('rainfall_probability')}%"
            )
            forecast_list.append(forecast_info)

        text = (
            f"地点：{location_name}\n\n"
            f"未来 {len(forecast_list)} 天天气预报：\n\n"
            + "\n\n".join(forecast_list)
        )
        text_block = TextBlock(type="text", text=text)
        return ToolResponse(content=[text_block])

    except Exception as e:
        text_block = TextBlock(type="text", text=f"天气预报查询失败：{str(e)}")
        return ToolResponse(
            content=[text_block]
        )


def send_email_tool(to_email: str, subject: str, content: str) -> ToolResponse:
    """{使用 SMTP 发送邮件到指定收件人}
    Args:
        to_email (str):
            {收件人的邮箱地址}
        subject (str):
            {邮件的主题}
        content (str):
            {邮件正文内容}
    """

    def smtp_send_email(to_person, sub, cont):
        email_user = os.getenv("EMAIL_USER")
        email_password = os.getenv("EMAIL_PASSWORD")
        email_host = os.getenv("EMAIL_HOST", "smtp.qq.com")
        email_port = int(os.getenv("EMAIL_PORT", "465"))

        if not email_user or not email_password:
            raise RuntimeError("缺少 EMAIL_USER 或 EMAIL_PASSWORD")

        msg = MIMEText(cont, "plain", "utf-8")
        msg["From"] = email_user
        msg["To"] = to_person
        msg["Subject"] = sub

        context = ssl.create_default_context()

        smtp = None
        try:
            smtp = smtplib.SMTP_SSL(
                host=email_host,
                port=email_port,
                context=context,
                timeout=10,
            )
            smtp.login(email_user, email_password)
            smtp.sendmail(email_user, [to_email], msg.as_string())
        finally:
            if smtp:
                try:
                    smtp.quit()
                except Exception as es:
                    import logging
                    logging.error(f"SMTP 退出失败：{str(es)}")
                    pass

    try:
        smtp_send_email(to_email, subject, content)
        content_dict = {
            "接收方": to_email,
            "主题": subject,
            "内容": content,
            "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        text_block = TextBlock(type="text", text="\n".join([f"{k}: {v}" for k, v in content_dict.items()]))
        return ToolResponse(
            content=[text_block]
        )
    except Exception as e:
        text_block = TextBlock(type="text", text=f"邮件发送失败：{str(e)}")
        return ToolResponse(content=[text_block])


def _normalize_ip_items(ips: Union[List[str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for item in ips:
        if isinstance(item, str):
            items.append({"ip": item, "count": None})
        elif isinstance(item, dict):
            ip = item.get("ip")
            if ip:
                items.append({"ip": ip, "count": item.get("count")})
        else:
            continue
    return items


@sanitize_tool_inputs
def query_ip_info(ips: Union[List[str], List[Dict[str, Any]]]) -> ToolResponse:
    """{批量查询 IP 信息}
    Args:
        ips (list): 支持 ["1.1.1.1", "8.8.8.8"] 或 [{"ip":"1.1.1.1","count":3}]
    """
    try:
        items = _normalize_ip_items(ips)
        if not items:
            text_block = TextBlock(type="text", text="IP 列表为空")
            return ToolResponse(content=[text_block])

        headers = {"User-Agent": "xiaoxiaoapi/1.0.0"}
        results = []
        for item in items:
            ip = item["ip"]
            url = f"https://v2.xxapi.cn/api/ip?ip={ip}"
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                address = data.get("data", {}).get("address")
                results.append({
                    "ip": ip,
                    "address": address,
                    "count": item.get("count"),
                })
            except Exception as e:
                results.append({
                    "ip": ip,
                    "error": str(e),
                    "count": item.get("count"),
                })
        text_block = TextBlock(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))
        return ToolResponse(content=[text_block])
    except Exception as e:
        text_block = TextBlock(type="text", text=f"IP 列表格式错误：{str(e)}")
        return ToolResponse(content=[text_block])
