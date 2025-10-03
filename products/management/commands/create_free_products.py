from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from products.models import Product, ProductCategory
from stores.models import Store


DEFAULT_CATEGORY_NAME = "카테고리 없음"


class Command(BaseCommand):
    help = "지정한 스토어에 무료 상품을 일괄 생성합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "store_id",
            type=str,
            help="상품을 생성할 스토어의 store_id",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="생성할 상품 개수 (기본값: 100)",
        )
        parser.add_argument(
            "--title-prefix",
            type=str,
            default="테스트 상품",
            help="상품 제목 앞에 붙일 접두어 (기본값: '테스트 상품')",
        )

    def handle(self, *args, **options):
        store_id: str = options["store_id"]
        count: int = options["count"]
        title_prefix: str = options["title_prefix"].strip() or "테스트 상품"

        if count <= 0:
            raise CommandError("count 값은 1 이상이어야 합니다.")

        try:
            store = Store.objects.get(store_id=store_id, deleted_at__isnull=True)
        except Store.DoesNotExist as exc:
            raise CommandError(f"store_id '{store_id}' 스토어를 찾을 수 없습니다.") from exc

        default_category, _ = ProductCategory.objects.get_or_create(
            store=store,
            name=DEFAULT_CATEGORY_NAME,
            defaults={"order": 0},
        )

        products_to_create = []

        for idx in range(1, count + 1):
            title = f"{title_prefix} {idx:03d}"
            description = (
                "테스트용 무료 상품입니다.\n"
                "자동 생성된 데이터로 실제 판매용이 아닙니다."
            )

            product = Product(
                store=store,
                category=default_category,
                title=title,
                description=description,
                price=0,
                price_display="sats",
                is_discounted=False,
                discounted_price=None,
                discounted_price_krw=None,
                completion_message="",
                force_free_shipping=True,
                stock_quantity=100,
                is_active=True,
            )
            products_to_create.append(product)

        with transaction.atomic():
            created_products = Product.objects.bulk_create(products_to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"스토어 '{store.store_name}' 에 무료 상품 {len(created_products)}개를 생성했습니다."
            )
        )
