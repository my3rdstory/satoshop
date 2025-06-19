from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = template.Library()

@register.inclusion_tag('myshop/components/opengraph_meta.html', takes_context=True)
def opengraph_meta(context, **kwargs):
    """
    오픈그래프 메타 태그를 생성하는 템플릿 태그
    
    사용법:
    {% load opengraph_tags %}
    {% opengraph_meta title="페이지 제목" description="페이지 설명" type="website" %}
    
    또는 동적으로:
    {% opengraph_meta title=dynamic_title description=dynamic_description %}
    """
    request = context.get('request')
    site_settings = context.get('site_settings')
    
    # 기본값 설정
    defaults = {
        'title': site_settings.site_title if site_settings else 'SatoShop',
        'description': site_settings.site_description if site_settings else '비트코인 라이트닝 결제 플랫폼',
        'type': 'website',
        'image': site_settings.og_default_image if site_settings and site_settings.og_default_image else None,
        'url': request.build_absolute_uri() if request else '',
        'site_name': site_settings.og_site_name if site_settings else 'SatoShop',
    }
    
    # 전달받은 파라미터로 기본값 오버라이드
    defaults.update(kwargs)
    
    return {
        'og_title': defaults['title'],
        'og_description': defaults['description'],
        'og_type': defaults['type'],
        'og_image': defaults['image'],
        'og_url': defaults['url'],
        'og_site_name': defaults['site_name'],
        'site_settings': site_settings,
        'request': request,
    }

@register.simple_tag(takes_context=True)
def auto_opengraph_meta(context, page_type=None, title=None, description=None, image=None):
    """
    페이지 타입에 따라 자동으로 오픈그래프 메타 태그를 생성
    
    사용법:
    {% load opengraph_tags %}
    {% auto_opengraph_meta "store_detail" %}
    {% auto_opengraph_meta "product_detail" title=product.title description=product.description %}
    """
    request = context.get('request')
    site_settings = context.get('site_settings')
    store = context.get('store')
    product = context.get('product')
    
    # 페이지 타입별 기본 설정
    page_configs = {
        'home': {
            'title': f"{site_settings.site_title} - {site_settings.site_description}" if site_settings else "SatoShop - 비트코인 라이트닝 결제 플랫폼",
            'description': site_settings.hero_description if site_settings and site_settings.hero_description else "누구나 쉽게 만드는 비트코인 온라인 스토어. 5분만에 스토어를 구축하고 라이트닝 네트워크로 즉시 결제받으세요.",
            'type': 'website'
        },
        'store_detail': {
            'title': f"{store.store_name} - SatoShop" if store else "스토어 - SatoShop",
            'description': f"{store.store_description[:100]}..." if store and store.store_description else "SatoShop 스토어에서 비트코인으로 쇼핑하세요",
            'type': 'website',
            'image': store.images.first().file_url if store and store.images.exists() else None
        },
        'product_detail': {
            'title': f"{product.title} - {store.store_name}" if product and store else "상품 - SatoShop",
            'description': f"{product.description[:100]}..." if product and product.description else "SatoShop에서 비트코인으로 구매하세요",
            'type': 'product',
            'image': product.images.first().file_url if product and hasattr(product, 'images') and product.images.exists() else None
        },
        'store_browse': {
            'title': "스토어 탐색 - SatoShop",
            'description': "SatoShop에서 다양한 스토어를 탐색하고 비트코인으로 쇼핑하세요. 창의적인 상품과 서비스를 발견해보세요.",
            'type': 'website'
        },
        'store_create': {
            'title': "스토어 만들기 - SatoShop",
            'description': "SatoShop에서 나만의 비트코인 온라인 스토어를 5분 만에 만들어보세요. 코딩 없이 쉽게 시작하세요.",
            'type': 'website'
        },
        'my_stores': {
            'title': "내 스토어 관리 - SatoShop",
            'description': "SatoShop에서 내가 운영하는 스토어를 관리하고 설정을 변경하세요.",
            'type': 'website'
        },
        'product_list': {
            'title': f"{store.store_name} 상품 목록 - SatoShop" if store else "상품 목록 - SatoShop",
            'description': f"{store.store_name}의 다양한 상품들을 둘러보고 비트코인으로 결제하세요." if store else "다양한 상품들을 둘러보고 비트코인으로 결제하세요.",
            'type': 'website'
        },
        'product_add': {
            'title': f"{store.store_name} 상품 추가 - SatoShop" if store else "상품 추가 - SatoShop",
            'description': f"{store.store_name}에 새로운 상품을 등록하고 비트코인 라이트닝 결제로 판매를 시작하세요." if store else "새로운 상품을 등록하고 비트코인 라이트닝 결제로 판매를 시작하세요.",
            'type': 'website'
        }
    }
    
    # 기본 설정 가져오기
    config = page_configs.get(page_type, {
        'title': site_settings.site_title if site_settings else 'SatoShop',
        'description': site_settings.site_description if site_settings else '비트코인 라이트닝 결제 플랫폼',
        'type': 'website'
    })
    
    # 파라미터로 전달된 값으로 오버라이드
    if title:
        config['title'] = title
    if description:
        config['description'] = description
    if image:
        config['image'] = image
    
    # 기본 이미지 설정
    if 'image' not in config or not config['image']:
        config['image'] = site_settings.og_default_image if site_settings and site_settings.og_default_image else None
    
    # 메타 태그 HTML 생성
    meta_tags = []
    
    # Open Graph 태그
    meta_tags.append(f'<meta property="og:title" content="{config["title"]}">')
    meta_tags.append(f'<meta property="og:description" content="{config["description"]}">')
    meta_tags.append(f'<meta property="og:type" content="{config["type"]}">')
    meta_tags.append(f'<meta property="og:url" content="{request.build_absolute_uri() if request else ""}">')
    if config.get('image'):
        meta_tags.append(f'<meta property="og:image" content="{config["image"]}">')
    meta_tags.append(f'<meta property="og:site_name" content="{site_settings.og_site_name if site_settings else "SatoShop"}">')
    meta_tags.append('<meta property="og:locale" content="ko_KR">')
    
    # Twitter Card 태그
    meta_tags.append('<meta name="twitter:card" content="summary_large_image">')
    meta_tags.append(f'<meta name="twitter:title" content="{config["title"]}">')
    meta_tags.append(f'<meta name="twitter:description" content="{config["description"]}">')
    if config.get('image'):
        meta_tags.append(f'<meta name="twitter:image" content="{config["image"]}">')
    
    return mark_safe('\n'.join(meta_tags)) 