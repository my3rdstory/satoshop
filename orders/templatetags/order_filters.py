from django import template

register = template.Library()

@register.filter
def split_order_number(order_number):
    """주문번호를 분리하여 딕셔너리로 반환"""
    if not order_number:
        return {'prefix': '', 'hash': ''}
    
    parts = order_number.split('-')
    
    if len(parts) >= 4:
        # store_id-ord-날짜-해시 형식
        prefix = '-'.join(parts[:-1])  # 해시 전까지
        hash_part = parts[-1]  # 마지막 해시 부분
    else:
        # 다른 형식의 경우 전체를 prefix로
        prefix = order_number
        hash_part = ''
    
    return {
        'prefix': prefix,
        'hash': hash_part
    }