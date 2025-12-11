"""
Test script for text summarization API endpoint.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_text_summarization():
    """Test the /text/summarize endpoint."""
    print("\n=== Testing Text Summarization Endpoint ===\n")

    # Test 1: Chinese text - medium length, neutral style
    print("Test 1: Chinese text - Medium length, Neutral style")
    chinese_text = """北京故宫是中国明清两代的皇家宫殿，旧称紫禁城，位于北京中轴线的中心。
故宫以三大殿为中心，占地面积约72万平方米，建筑面积约15万平方米，有大小宫殿七十多座，房屋九千余间。
是世界上现存规模最大、保存最为完整的木质结构古建筑之一。故宫于1961年被列为第一批全国重点文物保护单位，
1987年被列为世界文化遗产。现辟为故宫博物院，收藏有大量珍贵文物。"""

    payload = {
        "text": chinese_text,
        "language": "chi",
        "length": "medium",
        "style": "neutral",
    }

    response = requests.post(
        f"{BASE_URL}/text/summarize",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nOriginal length: {data['word_count_original']} characters")
        print(f"Summary length: {data['word_count_summary']} characters")
        print(
            f"Compression ratio: {(1 - data['word_count_summary']/data['word_count_original'])*100:.1f}%"
        )
        print(f"\nSummary:\n{data['summary']}")
        print(f"\nKey Points ({len(data['key_points'])}):")
        for i, point in enumerate(data["key_points"], 1):
            print(f"  {i}. {point}")
    else:
        print(f"Error: {response.text}")

    # Test 2: Chinese text - short length, simple style
    print("\n\nTest 2: Chinese text - Short length, Simple style")
    payload = {
        "text": chinese_text,
        "language": "chi",
        "length": "short",
        "style": "simple",
    }

    response = requests.post(
        f"{BASE_URL}/text/summarize",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nShort Summary:\n{data['summary']}")
    else:
        print(f"Error: {response.text}")

    # Test 3: Chinese text - medium length
    print("\n\nTest 3: Chinese text - Medium length, Neutral style")
    chinese_text = """9月的第2天，随着中国地产大亨王健林儿子王思聪的一则爆料，京东商城创始人，电商巨头刘强东被爆出在美国明尼苏达州性侵留学生。这样一则香艳的新闻迅速登上了中国社交媒体的头条，甚至成为爆款。人们在大肆讨论着霸道总裁，他年轻貌美拥有高学历的妻子，以及那位不知名的女大学生到底是何方神圣。
随后京东发言人，做出回应，刘强东在美国遭到了非实指控，并且已经保释。第二天，中国媒体已经联系上了刘强东在美国的律师并且得到了他在明尼苏达州警察局穿着囚犯服的照片！
再之后，刘强东回国，并且如往常一样参加了在京东举办的商务活动。人们在对此次事件做着各种假设：性侵对于一个大名鼎鼎的老板来说，实在没有必要。商业诬陷，做空股票或者资本入侵等等。
大多数参与讨论的人，对刘强东的印象还是很正面的，因为他民营企业家的身份。在中国迅速发展的物流行业中，京东为企业员工缴纳高昂的五险一金，这在行业中实属罕见，一年单此项费用就达到60亿人民币以上。刘强东来自江苏省宿迁市的一个农村，大学入读人民大学，读大学时带着亲戚们凑的500块生活费和咸鸭蛋开始了自己贫苦打拼的大学生活。此后他迷上了计算机，毕业之后没有像预想的一样走入仕途，而是在中关村的一个小商铺里开始了自己的刻录光盘生意，取名京东多媒体。京是他初恋女友姓名中的一个字，东是他自己。但是穷小子并没有留住美丽的姑娘，两人最后分手。
此后，刘强东经过多年打拼，终于成立了京东商场，并经过融资风险存活下来。"""

    payload = {
        "text": chinese_text,
        "language": "chi",
        "length": "medium",
        "style": "neutral",
    }

    response = requests.post(
        f"{BASE_URL}/text/summarize",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nOriginal length: {data['word_count_original']} words")
        print(f"Summary length: {data['word_count_summary']} words")
        print(f"\nSummary:\n{data['summary']}")
        print(f"\nKey Points:")
        for i, point in enumerate(data["key_points"], 1):
            print(f"  {i}. {point}")
    else:
        print(f"Error: {response.text}")

    # Test 4: Long summary, academic style
    print("\n\nTest 4: Chinese text - Long length, Academic style")
    payload = {
        "text": chinese_text,
        "language": "chi",
        "length": "long",
        "style": "academic",
    }

    response = requests.post(
        f"{BASE_URL}/text/summarize",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nLong Academic Summary:\n{data['summary']}")
    else:
        print(f"Error: {response.text}")

    # Test 5: Short text
    print("\n\nTest 5: Short Chinese text")
    short_text = "我喜欢学习中文。"

    payload = {
        "text": short_text,
        "language": "chi",
        "length": "short",
        "style": "simple",
    }

    response = requests.post(
        f"{BASE_URL}/text/summarize",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nOriginal: {data['original_text']}")
        print(f"Summary: {data['summary']}")
        print(f"Key Points: {', '.join(data['key_points'])}")
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    test_text_summarization()
