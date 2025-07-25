#!/usr/bin/env python
"""
프로덕션 환경에서 누락된 PurchaseHistory를 생성하는 스크립트

사용법:
1. 렌더닷컴 Shell에서 실행:
   python scripts/fix_purchase_history_production.py

2. 특정 사용자만 처리:
   python scripts/fix_purchase_history_production.py --user username

3. Dry run (실제 생성하지 않고 확인만):
   python scripts/fix_purchase_history_production.py --dry-run
"""

import os
import sys
import django
import argparse

# Django 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'satoshop.settings')
django.setup()

from django.db import transaction
from orders.models import Order, PurchaseHistory
from django.contrib.auth.models import User


def fix_purchase_history(dry_run=False, username=None):
    print("=" * 60)
    print("PurchaseHistory 누락 확인 및 생성")
    print("=" * 60)
    
    # 쿼리 준비
    paid_orders = Order.objects.filter(status='paid')
    
    if username:
        user = User.objects.filter(username=username).first()
        if not user:
            print(f"사용자 '{username}'를 찾을 수 없습니다.")
            return
        paid_orders = paid_orders.filter(user=user)
        print(f"사용자 {username}의 주문만 처리합니다.")
    
    total_orders = paid_orders.count()
    missing_count = 0
    created_count = 0
    errors = []
    
    print(f"총 결제 완료 주문: {total_orders}건")
    
    if dry_run:
        print("\n[DRY RUN 모드] 실제로 생성하지 않습니다.\n")
    
    try:
        with transaction.atomic():
            for i, order in enumerate(paid_orders):
                # PurchaseHistory 존재 확인
                if not PurchaseHistory.objects.filter(order=order).exists():
                    missing_count += 1
                    
                    if dry_run:
                        print(f"  - {order.order_number} (User: {order.user.username}, "
                              f"Store: {order.store.store_name})")
                    else:
                        try:
                            PurchaseHistory.objects.create(
                                user=order.user,
                                order=order,
                                store_name=order.store.store_name,
                                total_amount=order.total_amount,
                                purchase_date=order.paid_at or order.created_at
                            )
                            created_count += 1
                            
                            # 진행 상황 표시
                            if created_count % 10 == 0:
                                print(f"진행 중: {created_count}건 생성...")
                                
                        except Exception as e:
                            error_msg = f"오류 - {order.order_number}: {str(e)}"
                            errors.append(error_msg)
                            print(error_msg)
                
                # 전체 진행률 표시
                if (i + 1) % 50 == 0:
                    progress = ((i + 1) / total_orders) * 100
                    print(f"전체 진행률: {progress:.1f}% ({i + 1}/{total_orders})")
    
    except Exception as e:
        print(f"\n치명적 오류 발생: {str(e)}")
        return
    
    # 결과 출력
    print("\n" + "=" * 60)
    print(f"누락된 PurchaseHistory: {missing_count}건")
    
    if not dry_run:
        print(f"성공적으로 생성: {created_count}건")
        if errors:
            print(f"실패: {len(errors)}건")
            print("\n실패한 주문 (처음 5개):")
            for error in errors[:5]:
                print(f"  {error}")
            if len(errors) > 5:
                print(f"  ... 외 {len(errors) - 5}건")
    
    # 최종 통계
    total_ph = PurchaseHistory.objects.count()
    print(f"\n현재 총 PurchaseHistory: {total_ph}건")
    
    if dry_run:
        print("\n실제로 생성하려면 --dry-run 옵션 없이 다시 실행하세요.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="누락된 PurchaseHistory 생성")
    parser.add_argument("--dry-run", action="store_true", 
                        help="실제로 생성하지 않고 확인만 합니다")
    parser.add_argument("--user", type=str, 
                        help="특정 사용자의 PurchaseHistory만 생성합니다")
    
    args = parser.parse_args()
    
    try:
        fix_purchase_history(dry_run=args.dry_run, username=args.user)
    except KeyboardInterrupt:
        print("\n\n작업이 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")