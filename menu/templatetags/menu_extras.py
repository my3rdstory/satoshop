from django import template
import re

register = template.Library()

@register.filter
def split_option_value(value):
    """
    옵션 값을 파싱하여 이름과 가격을 분리합니다.
    예: "빨강(+1000)" -> {"name": "빨강", "price": "1000"}
    예: "파랑" -> {"name": "파랑", "price": "0"}
    """
    if not value:
        return {"name": "", "price": "0"}
    
    # (+숫자) 패턴 찾기
    pattern = r'^(.+?)\(\+([0-9.]+)\)$'
    match = re.match(pattern, str(value))
    
    if match:
        name = match.group(1).strip()
        price = match.group(2)
        # 소수점이 있으면 정수로 변환
        try:
            price = str(int(float(price)))
        except ValueError:
            price = "0"
        return {"name": name, "price": price}
    else:
        return {"name": str(value), "price": "0"} 